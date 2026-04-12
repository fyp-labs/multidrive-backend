# OCR Setup Guide for Image-Based PDFs

This guide explains how to set up OCR (Optical Character Recognition) support for extracting text from image-based PDFs.

## Why OCR is Needed

Some PDFs contain scanned images or screenshots rather than actual text. Regular PDF text extraction returns no content from these files. OCR solves this by:
1. Converting each PDF page to an image
2. Using Tesseract OCR to recognize and extract text from the images
3. Combining the extracted text for indexing

## Prerequisites

### 1. Install Tesseract OCR Engine

Tesseract is an open-source OCR engine that pytesseract uses under the hood.

#### Windows Installation

**Option A: Using Installer (Recommended)**
1. Download the Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (e.g., `tesseract-ocr-w64-setup-5.3.3.20231005.exe`)
3. During installation, note the installation path (usually `C:\Program Files\Tesseract-OCR`)
4. Add Tesseract to your system PATH or configure it in your `.env` file

**Option B: Using Chocolatey**
```bash
choco install tesseract
```

**Option C: Using Scoop**
```bash
scoop install tesseract
```

#### Linux Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev
```

**Fedora/RHEL:**
```bash
sudo dnf install tesseract
sudo dnf install tesseract-devel
```

#### macOS Installation

```bash
brew install tesseract
```

### 2. Install Python Dependencies

The required Python packages are already in `requirements.txt`:
- `pytesseract==0.3.13` - Python wrapper for Tesseract
- `pdf2image==1.17.0` - Convert PDF pages to images
- `pymupdf==1.25.4` - Advanced PDF processing library
- `Pillow==11.0.0` - Image processing (already included)

Install them:
```bash
pip install -r requirements.txt
```

### 3. Configure Tesseract Path (Windows Only)

If Tesseract is not in your system PATH, you need to specify its location.

**Option A: Add to .env file**
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**Option B: Add to System PATH**
1. Open System Properties → Environment Variables
2. Edit the `PATH` variable
3. Add: `C:\Program Files\Tesseract-OCR`
4. Restart your terminal/IDE

## Verification

### Test Tesseract Installation

```bash
tesseract --version
```

Expected output:
```
tesseract 5.x.x
 leptonica-1.x.x
  ...
```

### Test Python Integration

Create a test script `test_ocr.py`:
```python
import pytesseract
from PIL import Image
import requests
from io import BytesIO

# Test with a sample image
response = requests.get('https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf')
img = Image.open(BytesIO(response.content))
text = pytesseract.image_to_string(img)
print(f"Extracted text: {text}")
```

Run it:
```bash
python test_ocr.py
```

## How It Works

The document extraction pipeline now works as follows:

1. **Regular Text Extraction** (Fast)
   - Try to extract text using PyPDF2
   - If sufficient text found (>50 chars), use it

2. **OCR Fallback** (Slower, for image-based PDFs)
   - If insufficient text (<50 chars), trigger OCR
   - Convert each PDF page to a high-resolution image (2x zoom)
   - Run Tesseract OCR on each image
   - Combine extracted text from all pages

## Performance Considerations

### OCR Speed
- **Regular PDFs**: ~1-2 seconds per document
- **Image-based PDFs with OCR**: ~5-30 seconds per document (depends on pages/quality)

### Tips for Better Performance
1. **Batch Processing**: Already implemented - processes documents in batches of 3
2. **Heartbeats**: Activity sends heartbeats during OCR to prevent timeouts
3. **Quality vs Speed**: Current settings use 2x zoom for good accuracy

### Tesseract Configuration (Advanced)

For better OCR results, you can configure Tesseract parameters:

```python
# In document_text_extractor.py
custom_config = r'--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
text = pytesseract.image_to_string(image, lang='eng', config=custom_config)
```

**Common PSM (Page Segmentation Mode) values:**
- `3` = Fully automatic page segmentation (default)
- `6` = Assume a single uniform block of text
- `11` = Sparse text. Find as much text as possible

## Supported Languages

By default, only English is configured. To add more languages:

### Install Additional Language Packs

**Windows:**
Download from: https://github.com/tesseract-ocr/tessdata
Place `.traineddata` files in: `C:\Program Files\Tesseract-OCR\tessdata`

**Linux:**
```bash
sudo apt install tesseract-ocr-[lang]
# Example: sudo apt install tesseract-ocr-ara  # Arabic
```

**Usage in code:**
```python
text = pytesseract.image_to_string(image, lang='eng+ara')  # English + Arabic
```

## Troubleshooting

### Error: "TesseractNotFoundError"
- **Cause**: Tesseract not installed or not in PATH
- **Fix**: Install Tesseract and add to PATH or configure `TESSERACT_CMD` in `.env`

### Error: "Failed to load lang model"
- **Cause**: Language data files missing
- **Fix**: Reinstall Tesseract with language packs

### Poor OCR Quality
- **Cause**: Low-resolution images, poor scan quality
- **Solutions**:
  - Increase zoom level in code: `matrix=fitz.Matrix(3, 3)`
  - Preprocess image (increase contrast, denoise)
  - Use better source PDFs

### OCR Taking Too Long
- **Cause**: High-resolution images, many pages
- **Solutions**:
  - Reduce zoom level: `matrix=fitz.Matrix(1.5, 1.5)`
  - Process fewer pages at once
  - Use faster PSM mode: `--psm 6`

## Monitoring OCR Progress

The activity logs OCR progress:
```
📄 Processing document: Ch#18 Topic Alcohol's
   Type: application/pdf, Size: 4247876 bytes
   📥 Downloaded 4247876 bytes
   ⚠️ Insufficient text found with regular extraction, trying OCR...
   🔍 Using OCR for image-based PDF...
   ✅ OCR completed: 25/25 pages extracted
   📝 Extracted 5420 words, 35678 characters
```

## Next Steps

After setup:
1. Run `pip install -r requirements.txt` to install Python packages
2. Verify Tesseract installation with `tesseract --version`
3. Restart the worker: `python -m app.temporal.google_drive.workers.GoogleDriveMetaDataWorker`
4. Retry the workflow - image-based PDFs will now be processed with OCR

## Additional Resources

- Tesseract Documentation: https://tesseract-ocr.github.io/
- PyMuPDF Documentation: https://pymupdf.readthedocs.io/
- pytesseract GitHub: https://github.com/madmaze/pytesseract
