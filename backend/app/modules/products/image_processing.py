from io import BytesIO

from fastapi import HTTPException
from PIL import Image

from app.modules.stores.image_processing import normalize_image, validate_store_image as validate_image


IMAGE_PRESETS = {'card': 800, 'large': 1600}


def process_image(data: bytes) -> dict[str, bytes]:
	variants = {}
	encoded_sizes = {}

	try:
		with normalize_image(data) as normalized:
			largest_size = max(IMAGE_PRESETS.values())
			normalized.thumbnail((largest_size, largest_size), Image.Resampling.LANCZOS)

			for variant, size in IMAGE_PRESETS.items():
				with normalized.copy() as resized:
					resized.thumbnail((size, size), Image.Resampling.LANCZOS)

					if resized.size not in encoded_sizes:
						with BytesIO() as output:
							resized.save(output, format='WEBP', quality=85, method=4)
							encoded_sizes[resized.size] = output.getvalue()

					variants[variant] = encoded_sizes[resized.size]
	except (OSError, ValueError, SyntaxError, EOFError):
		raise HTTPException(status_code=422, detail='Não foi possível processar a imagem.') from None

	return variants
