from pypdf import PdfReader, PdfWriter
from PIL import ImageGrab
from io import BytesIO
from ctypes import windll

def screen_shot(rect: tuple):
    user32 = windll.user32

    # take screen shot
    img = ImageGrab.grab(rect, all_screens=True)
    ImageGrab.grab()

    # export screen shot as bytes
    buffer = 0
    with BytesIO() as output:
        img.save(output, format = 'PDF')
        buffer = output.getvalue()

    return buffer

def merge(imagerect, image_pdf: bytes, frame_path: str, output_path: str):
    with open(frame_path, 'rb') as frame_pdf:
        # read pdf
        frame = PdfReader(frame_pdf, 'rb').pages[0]

        image = PdfReader(BytesIO(image_pdf)).pages[0]

        # add transformations to image
        image.scale_to(imagerect[2], imagerect[3])

        # add image to the page
        frame.merge_translated_page(image, imagerect[0], imagerect[1])

        # export pdf
        writer = PdfWriter()
        writer.add_page(frame)
        
        with open(output_path, 'wb') as outFile:
            writer.write(outFile)