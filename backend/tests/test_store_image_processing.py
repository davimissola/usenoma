from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageCms, ImageDraw

from app.modules.stores.image_processing import process_store_image, validate_store_image


def process_image(data, image_type):
	with BytesIO(data) as buffer:
		file = UploadFile(filename='imagem', file=buffer)
		return process_store_image(validate_store_image(file), image_type)


@pytest.mark.parametrize('format', ['JPEG', 'PNG', 'WEBP'])
def test_input_formats_are_reencoded_without_metadata(format):
	with Image.new('RGB', (800, 400), 'red') as source, BytesIO() as buffer:
		exif = Image.Exif()
		exif[0x010E] = 'metadado-privado'
		profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
		source.save(buffer, format=format, exif=exif, icc_profile=profile)
		variants = process_image(buffer.getvalue(), 'logo')

	for data, width, height in variants.values():
		with BytesIO(data) as buffer, Image.open(buffer) as image:
			image.load()
			assert image.format == 'WEBP'
			assert image.mode == 'RGB'
			assert image.size == (width, height)
			assert not image.getexif()
			assert not {'exif', 'icc_profile', 'xmp'} & image.info.keys()
			assert b'metadado-privado' not in data


@pytest.mark.parametrize('image_type, expected', [('logo', {'small': (256, 128), 'medium': (512, 256)}), ('cover', {'medium': (960, 480), 'large': (1920, 960)})])
def test_presets_preserve_proportions_and_generate_only_expected_variants(image_type, expected):
	with Image.new('RGB', (2400, 1200), 'blue') as source, BytesIO() as buffer:
		source.save(buffer, format='PNG')
		variants = process_image(buffer.getvalue(), image_type)

	assert set(variants) == set(expected)

	for variant, (data, width, height) in variants.items():
		assert (width, height) == expected[variant]

		with BytesIO(data) as buffer, Image.open(buffer) as image:
			assert image.size == expected[variant]


@pytest.mark.parametrize('image_type', ['logo', 'cover'])
def test_small_input_is_not_upscaled_and_duplicate_sizes_reuse_encoded_bytes(image_type):
	with Image.new('RGB', (80, 40), 'green') as source, BytesIO() as buffer:
		source.save(buffer, format='PNG')
		variants = process_image(buffer.getvalue(), image_type)

	encoded = list(variants.values())
	assert all((width, height) == (80, 40) for data, width, height in encoded)
	assert encoded[0][0] is encoded[1][0]


@pytest.mark.parametrize('mode', ['RGBA', 'P'])
def test_png_transparency_is_preserved(mode):
	with Image.new('RGBA', (100, 60), (0, 0, 0, 0)) as source, BytesIO() as buffer:
		ImageDraw.Draw(source).rectangle((30, 10, 70, 50), fill=(255, 0, 0, 255))

		if mode == 'P':
			with source.convert('P') as palette:
				palette.save(buffer, format='PNG')
		else:
			profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
			source.save(buffer, format='PNG', icc_profile=profile)

		variants = process_image(buffer.getvalue(), 'logo')

	for data, width, height in variants.values():
		with BytesIO(data) as buffer, Image.open(buffer) as image:
			assert image.mode == 'RGBA'
			assert image.getpixel((0, 0))[3] == 0
			assert image.getpixel((50, 30))[3] == 255


@pytest.mark.parametrize('orientation, expected_size, blue_point, red_point', [(6, (60, 100), (30, 75), (30, 25)), (2, (100, 60), (25, 30), (75, 30))])
def test_exif_orientation_corrects_rotation_and_mirroring_before_saving(orientation, expected_size, blue_point, red_point):
	with Image.new('RGB', (100, 60), 'red') as source, BytesIO() as buffer:
		ImageDraw.Draw(source).rectangle((50, 0, 99, 59), fill='blue')
		exif = Image.Exif()
		exif[0x0112] = orientation
		source.save(buffer, format='JPEG', quality=95, exif=exif)
		variants = process_image(buffer.getvalue(), 'logo')

	for data, width, height in variants.values():
		assert (width, height) == expected_size

		with BytesIO(data) as buffer, Image.open(buffer) as image:
			assert image.getpixel(blue_point)[2] > image.getpixel(blue_point)[0]
			assert image.getpixel(red_point)[0] > image.getpixel(red_point)[2]
			assert not image.getexif()


@pytest.mark.parametrize('format', ['PNG', 'WEBP', 'GIF', 'MPO'])
def test_animated_or_multipage_input_is_rejected(format):
	with Image.new('RGB', (40, 30), 'red') as first, Image.new('RGB', (40, 30), 'blue') as second, BytesIO() as buffer:
		first.save(buffer, format=format, save_all=True, append_images=[second], duration=100)

		with pytest.raises(HTTPException) as error:
			process_image(buffer.getvalue(), 'logo')

	assert error.value.status_code == 415


def test_grayscale_input_is_normalized_to_rgb():
	with Image.new('L', (100, 60), 120) as source, BytesIO() as buffer:
		source.save(buffer, format='PNG')
		variants = process_image(buffer.getvalue(), 'logo')

	for data, width, height in variants.values():
		with BytesIO(data) as buffer, Image.open(buffer) as image:
			assert image.mode == 'RGB'


def test_invalid_icc_is_discarded_without_rejecting_valid_pixels():
	with Image.new('RGB', (100, 60), 'red') as source, BytesIO() as buffer:
		source.save(buffer, format='PNG', icc_profile=b'perfil-invalido')
		variants = process_image(buffer.getvalue(), 'logo')

	for data, width, height in variants.values():
		with BytesIO(data) as buffer, Image.open(buffer) as image:
			assert image.mode == 'RGB'
			assert 'icc_profile' not in image.info
