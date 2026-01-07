# Scheme Seeding Script

This script downloads and imports government scheme data from Hugging Face dataset into MongoDB.

## Prerequisites

1. MongoDB connection string in `.env` file:
   ```
   MONGODB_URL=your_mongodb_connection_string
   ```

2. Dataset file (choose one method below)

## Getting the Dataset

### Method 1: Download All PDFs (Recommended for Full Dataset)

This method downloads and processes ALL PDFs from the Hugging Face dataset:

```bash
cd Backend/scripts
python download_all_pdfs.py
```

This script will:
- Download all PDFs from the `text_data` folder
- Extract text from each PDF
- Parse structured data (scheme name, eligibility, benefits, etc.)
- Save to `Backend/data/schemes_data.json`

**Note:** This processes hundreds of PDFs and may take 10-30 minutes depending on your internet speed.

### Method 2: Manual Download (Quick Test)

1. Visit: https://huggingface.co/datasets/shrijayan/gov_myscheme
2. Click on **"Files and versions"** tab
3. Download one of these files:
   - `train.json` (if available)
   - `train.csv` (if available)
   - Any JSON/CSV file from the dataset
4. Place the file in `Backend/data/schemes_data.json`
   - If it's a CSV, convert it to JSON first
   - If it's named differently, rename it to `schemes_data.json`

### Method 2: Using Python (Alternative)

If you have Python installed, you can download the dataset:

```bash
pip install datasets pandas

python -c "
from datasets import load_dataset
import json

dataset = load_dataset('shrijayan/gov_myscheme', split='train')
data = [item for item in dataset]

with open('Backend/data/schemes_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Downloaded {len(data)} schemes')
"
```

### Method 3: Using Hugging Face CLI

```bash
pip install huggingface_hub

huggingface-cli download shrijayan/gov_myscheme --local-dir ./Backend/data
```

## Running the Script

### Basic Usage

```bash
cd Backend
npm run seed
```

### Configuration Options

Edit `Backend/scripts/seedSchemes.js` to configure:

```javascript
const CONFIG = {
  CLEAR_EXISTING: false,  // Set to true to clear existing data before import
  LIMIT: null,            // Set to a number (e.g., 100) to limit imports for testing
  BATCH_SIZE: 100,        // Number of schemes to insert at once
};
```

### Examples

**Test with first 50 schemes:**
```javascript
LIMIT: 50
```

**Clear existing and import all:**
```javascript
CLEAR_EXISTING: true,
LIMIT: null
```

## What the Script Does

1. **Loads Dataset**: Reads from `Backend/data/schemes_data.json` or uses sample data
2. **Transforms Data**: Maps dataset fields to your `Schemev2` schema
3. **Validates**: Checks required fields and removes duplicates
4. **Imports**: Inserts schemes into MongoDB in batches
5. **Post-processes**: Applies data transformations (date fixes, etc.)

## Troubleshooting

### "No dataset file found"
- Make sure you've downloaded the dataset and placed it in `Backend/data/schemes_data.json`
- The script will use sample data if no file is found

### "MongoDB connection error"
- Check your `.env` file has `MONGODB_URL` set correctly
- Ensure MongoDB is running and accessible

### "Invalid dataset format"
- Ensure the JSON file is an array of objects: `[{...}, {...}]`
- Not a single object: `{...}`

### Import errors
- Check MongoDB logs for specific errors
- Some schemes might fail if they don't match the schema
- The script will continue and report how many succeeded

## File Structure

```
Backend/
├── scripts/
│   ├── seedSchemes.js    # Main seeding script
│   └── README.md         # This file
├── data/
│   └── schemes_data.json # Place your dataset here
└── package.json
```

## Notes

- The script handles duplicates automatically
- Invalid schemes are skipped (logged in console)
- Progress is shown during import
- Post-processing fixes dates and data structures automatically

