from io import BytesIO
from warnings import catch_warnings, simplefilter

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from app.modules.stores.schemas import StoreImageType, StoreImageVariantName


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 6000
MAX_IMAGE_PIXELS = 20_000_000
IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
IMAGE_PRESETS = {'logo': {'small': 256, 'medium': 512}, 'cover': {'medium': 960, 'large': 1920}}
WEBP_QUALITY = {'logo': 90, 'cover': 85}


def validate_store_image(file: UploadFile) -> bytes:
	# A leitura limitada evita carregar todo um arquivo grande antes de recusá-lo.
	data = file.file.read(MAX_IMAGE_BYTES + 1)

	if len(data) > MAX_IMAGE_BYTES:
		raise HTTPException(status_code=413, detail='A imagem deve ter no máximo 5 MiB.')

	if not data:
		raise HTTPException(status_code=422, detail='Envie um arquivo de imagem válido.')

	if file.content_type == 'image/svg+xml':
		raise HTTPException(status_code=415, detail='São aceitas apenas imagens JPEG, PNG ou WebP estáticas.')

	try:
		with catch_warnings():
			simplefilter('error', Image.DecompressionBombWarning)

			with BytesIO(data) as buffer, Image.open(buffer) as image:
				# Formato e dimensões vêm do conteúdo, não do nome ou MIME enviado pelo navegador.
				if image.format not in IMAGE_FORMATS or getattr(image, 'n_frames', 1) != 1:
					raise HTTPException(status_code=415, detail='São aceitas apenas imagens JPEG, PNG ou WebP estáticas.')

				width, height = image.size

				if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION or width * height > MAX_IMAGE_PIXELS:
					raise HTTPException(status_code=413, detail='A imagem deve ter até 6000 pixels por lado e 20 milhões de pixels no total.')

				image.verify()
	except (Image.DecompressionBombError, Image.DecompressionBombWarning):
		raise HTTPException(status_code=413, detail='A resolução da imagem excede o limite permitido.') from None
	except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
		raise HTTPException(status_code=422, detail='Envie um arquivo de imagem válido.') from None

	return data


def process_store_image(data: bytes, image_type: StoreImageType) -> dict[StoreImageVariantName, tuple[bytes, int, int]]:
	variants = {}
	encoded_sizes = {}
	presets = IMAGE_PRESETS[image_type]

	try:
		with BytesIO(data) as buffer, Image.open(buffer) as image:
			# Decodifica de verdade antes de qualquer upload e aplica rotação/espelhamento EXIF.
			image.load()
			ImageOps.exif_transpose(image, in_place=True)

			if 'A' in image.getbands() or 'transparency' in image.info:
				mode = 'RGBA'
			else:
				mode = 'RGB'

			icc_profile = image.info.get('icc_profile')

			if icc_profile:
				try:
					# Converte cores para sRGB antes de retirar o perfil, preservando também o alpha.
					with BytesIO(icc_profile) as profile:
						normalized = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(profile), ImageCms.createProfile('sRGB'), outputMode=mode, flags=ImageCms.Flags.COPY_ALPHA)
				except (ImageCms.PyCMSError, OSError, ValueError):
					# Um ICC inválido/incompatível não invalida os pixels de uma imagem decodificada.
					normalized = image.convert(mode)
			else:
				normalized = image.convert(mode)

		# A imagem original já foi fechada; as cópias abaixo ficam limitadas ao maior preset.
		with normalized:
			normalized.info.clear()
			largest_size = max(presets.values())
			normalized.thumbnail((largest_size, largest_size), Image.Resampling.LANCZOS)

			for variant, size in presets.items():
				with normalized.copy() as resized:
					# thumbnail mantém proporção, não corta e não aumenta imagens pequenas.
					resized.thumbnail((size, size), Image.Resampling.LANCZOS)
					dimensions = resized.size

					if dimensions not in encoded_sizes:
						with BytesIO() as output:
							resized.save(output, format='WEBP', quality=WEBP_QUALITY[image_type], method=4)
							encoded_sizes[dimensions] = output.getvalue()

					# Presets iguais para uma imagem pequena compartilham os mesmos bytes/arquivo.
					variants[variant] = (encoded_sizes[dimensions], resized.width, resized.height)
	except (OSError, ValueError, SyntaxError, EOFError):
		raise HTTPException(status_code=422, detail='Não foi possível processar a imagem.') from None

	return variants
