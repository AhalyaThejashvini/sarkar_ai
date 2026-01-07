# Quick Start Guide - Loading Scheme Data

## Step 1: Get the Dataset

### Option A: Using Python (Easiest)

```bash
# Install Python dependencies
pip install datasets

# Download the dataset
cd Backend/scripts
python download_dataset.py
```

### Option B: Manual Download

1. Go to: https://huggingface.co/datasets/shrijayan/gov_myscheme
2. Click "Files and versions"
3. Download a JSON or CSV file
4. Save it as `Backend/data/schemes_data.json`

## Step 2: Run the Seed Script

```bash
cd Backend
npm run seed
```

That's it! The script will:
- ✅ Load the dataset
- ✅ Transform to match your schema
- ✅ Import into MongoDB
- ✅ Apply data transformations

## Step 3: Verify

Check your database or test the API:

```bash
curl http://localhost:5000/api/v2/schemes/get-all-schemes?page=1&limit=5
```

## Troubleshooting

**"No dataset file found"**
→ Make sure `Backend/data/schemes_data.json` exists

**"MongoDB connection error"**
→ Check your `.env` file has `MONGODB_URL`

**Want to test with limited data?**
→ Edit `Backend/scripts/seedSchemes.js` and set `LIMIT: 50`

