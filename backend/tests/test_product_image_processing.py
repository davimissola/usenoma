from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.modules.products.image_processing import process_image, validate_image


@pytest.mark.parametrize('format', ['JPEG', 'PNG', 'WEBP'])
def test_product_presets_are_webp_and_preserve_proportions(format):
	with BytesIO() as buffer, Image.new('RGB', (2000, 1000), 'red') as image:
		exif = Image.Exif()
		exif[305] = 'Metadado que deve ser removido'
		image.save(buffer, format=format, exif=exif)
		data = buffer.getvalue()

	variants = process_image(validate_image(UploadFile(BytesIO(data), filename='foto')))
	assert set(variants) == {'card', 'large'}

	for variant, size in [('card', (800, 400)), ('large', (1600, 800))]:
		with BytesIO(variants[variant]) as buffer, Image.open(buffer) as image:
			image.load()
			assert image.format == 'WEBP'
			assert image.size == size
			assert not image.getexif()
			assert not {'exif', 'icc_profile', 'xmp'} & image.info.keys()


def test_product_processing_preserves_alpha_and_never_upscales():
	with BytesIO() as buffer, Image.new('RGBA', (100, 200), (255, 0, 0, 0)) as image:
		image.save(buffer, format='PNG')
		variants = process_image(buffer.getvalue())

	for data in variants.values():
		with BytesIO(data) as buffer, Image.open(buffer) as image:
			image.load()
			assert image.size == (100, 200)
			assert image.getpixel((0, 0))[3] == 0


def test_product_processing_corrects_exif_orientation():
	with BytesIO() as buffer, Image.new('RGB', (1200, 600), 'red') as image:
		exif = Image.Exif()
		exif[274] = 6
		image.save(buffer, format='JPEG', exif=exif)
		variants = process_image(buffer.getvalue())

	with BytesIO(variants['card']) as buffer, Image.open(buffer) as image:
		assert image.size == (400, 800)


def test_animated_product_image_is_rejected():
	with BytesIO() as buffer, Image.new('RGB', (10, 10), 'red') as first, Image.new('RGB', (10, 10), 'blue') as second:
		first.save(buffer, format='WEBP', save_all=True, append_images=[second], duration=100)

		with pytest.raises(HTTPException) as error:
			validate_image(UploadFile(BytesIO(buffer.getvalue()), filename='animated.webp'))

	assert error.value.status_code == 415
