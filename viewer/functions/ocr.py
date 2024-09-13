from PIL import Image
from pytesseract import pytesseract
from django.conf import settings

def get_text_in_image(image_path):

	if not hasattr(settings, "TESSERACT_BINARY"):
		return None

	pytesseract.tesseract_cmd = settings.TESSERACT_BINARY
	img = Image.open(image_path)
	if hasattr(settings, "TESSERACT_LANGUAGE"):
		try:
			return pytesseract.image_to_string(img, lang=settings.TESSERACT_LANGUAGE)
		except:
			return ''
	else:
		try:
			return pytesseract.image_to_string(img)
		except:
			return ''
	return ''
