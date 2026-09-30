# Synthetic OCR fixtures

Generated locally for this project with Windows System.Drawing, Arial 32 pt,
black text on white background, 1200 × 300 pixels. No personal or upstream data.

`reference.png` and `reference.jpg` contain:

    OCR REFERENCE 930
    Rechnung 4711. Betrag 125 Euro.

`blank.png` is a blank white image of the same dimensions. Tests use it to ensure
that an image without recognized text is rejected instead of silently attached.

`unicode.png` contains `Grüße für Österreich`, Arial 36 pt on a 1200 × 220 white
image, to qualify Unicode transport through the native OCR subprocess.

These fixtures qualify printed text extraction and immutable original downloads;
they do not qualify handwriting, complex layouts or general image understanding.
