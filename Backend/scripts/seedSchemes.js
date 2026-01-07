import mongoose from 'mongoose';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import Schemev2 from '../models/schemev2.model.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const CONFIG = {
  // Hugging Face dataset URL - using the raw JSON file
  DATASET_URL: 'https://huggingface.co/datasets/shrijayan/gov_myscheme/resolve/main/data/train-00000-of-00001.parquet',
  // Alternative: Try to get JSON format
  DATASET_JSON_URL: 'https://huggingface.co/api/datasets/shrijayan/gov_myscheme',
  // Local cache file
  CACHE_FILE: path.join(__dirname, '../data/dataset_cache.json'),
  // Batch size for insertion
  BATCH_SIZE: 100,
  // Options
  CLEAR_EXISTING: false, // Set to true to clear existing data
  LIMIT: null, // Set to a number to limit imports (e.g., 100 for testing)
};

/**
 * Download dataset from Hugging Face
 */
const downloadDataset = async () => {
  console.log('📥 Downloading dataset from Hugging Face...');
  
  try {
    // Try multiple approaches to get the data
    // Approach 1: Try to get via Hugging Face API
    const apiUrl = 'https://datasets-server.huggingface.co/parquet?dataset=shrijayan%2Fgov_myscheme';
    
    console.log('   Fetching dataset info...');
    const infoResponse = await fetch(apiUrl);
    
    if (!infoResponse.ok) {
      throw new Error(`Failed to fetch dataset info: ${infoResponse.statusText}`);
    }
    
    const info = await infoResponse.json();
    console.log('   Dataset info retrieved');
    
    // Try to get the parquet file URL
    let datasetUrl = null;
    if (info.parquet_files && info.parquet_files.length > 0) {
      datasetUrl = info.parquet_files[0].url;
    }
    
    if (!datasetUrl) {
      // Fallback: Try direct download of JSON if available
      console.log('   ⚠️  Parquet file not found, trying alternative methods...');
      throw new Error('Parquet file URL not found. Please download the dataset manually.');
    }
    
    console.log('   Downloading dataset file...');
    const response = await fetch(datasetUrl);
    
    if (!response.ok) {
      throw new Error(`Failed to download dataset: ${response.statusText}`);
    }
    
    // For now, we'll use a manual download approach
    // Since Hugging Face datasets are typically in Parquet format
    // We'll provide instructions for manual download
    
    console.log('   ⚠️  Automatic download of Parquet files requires additional libraries.');
    console.log('   📋 Please download the dataset manually:');
    console.log('   1. Visit: https://huggingface.co/datasets/shrijayan/gov_myscheme');
    console.log('   2. Click on "Files and versions" tab');
    console.log('   3. Download the JSON or CSV file');
    console.log('   4. Place it in Backend/data/ as "schemes_data.json"');
    console.log('   Or use the alternative method below...\n');
    
    return null;
  } catch (error) {
    console.error('   ❌ Error downloading dataset:', error.message);
    console.log('   📋 Using alternative: Manual download required');
    return null;
  }
};

/**
 * Load dataset from local file or cache
 */
const loadDataset = async () => {
  // Check for local data file first
  const localDataFile = path.join(__dirname, '../data/schemes_data.json');
  const cacheFile = CONFIG.CACHE_FILE;
  
  // Ensure data directory exists
  const dataDir = path.dirname(localDataFile);
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  
  // Try local data file
  if (fs.existsSync(localDataFile)) {
    console.log('📂 Loading dataset from local file...');
    const data = fs.readFileSync(localDataFile, 'utf8');
    return JSON.parse(data);
  }
  
  // Try cache file
  if (fs.existsSync(cacheFile)) {
    console.log('📂 Loading dataset from cache...');
    const data = fs.readFileSync(cacheFile, 'utf8');
    return JSON.parse(data);
  }
  
  // Try to download
  const downloaded = await downloadDataset();
  if (downloaded) {
    // Save to cache
    const dataDir = path.dirname(cacheFile);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    fs.writeFileSync(cacheFile, JSON.stringify(downloaded, null, 2));
    return downloaded;
  }
  
  // If all fails, return sample data for testing
  console.log('⚠️  No dataset file found. Using sample data for testing...');
  return getSampleData();
};

/**
 * Get sample data for testing
 */
const getSampleData = () => {
  return [
    {
      schemeName: "Pradhan Mantri Awas Yojana",
      schemeShortTitle: "PMAY",
      state: "All India",
      level: "Central",
      nodalMinistryName: { label: "Ministry of Housing and Urban Affairs" },
      tags: ["housing", "urban", "subsidy"],
      schemeCategory: ["Housing", "Urban Development"],
      detailedDescription_md: "A flagship mission of Government of India to provide affordable housing to the urban poor.",
      eligibilityDescription_md: "Families belonging to EWS/LIG categories in urban areas. Annual household income up to ₹3 lakh for EWS and ₹6 lakh for LIG.",
      benefits: [
        {
          title: "Interest Subsidy",
          description: "Interest subsidy of 6.5% for a loan tenure of 20 years"
        }
      ],
      documents_required: [
        {
          document: "Aadhaar Card",
          description: "Valid Aadhaar card of all family members"
        }
      ],
      applicationProcess: [
        {
          mode: "Online",
          process: [
            "Visit the official PMAY website",
            "Register with Aadhaar number",
            "Fill the application form"
          ]
        }
      ],
      faqs: [
        {
          question: "Who is eligible for PMAY?",
          answer: "Families with annual income up to ₹3 lakh (EWS) or ₹6 lakh (LIG) are eligible."
        }
      ],
      references: [
        {
          title: "Official Website",
          url: "https://pmaymis.gov.in"
        }
      ],
      openDate: "2024-01-01",
      closeDate: "2025-12-31"
    }
  ];
};

/**
 * Transform dataset item to Schemev2 schema
 */
const transformScheme = (item) => {
  try {
    const scheme = {
      schemeName: item.schemeName || item.name || item.title || 'Untitled Scheme',
      schemeShortTitle: item.schemeShortTitle || item.shortTitle || item.code || 'N/A',
      state: item.state || item.states || null,
      level: item.level || item.schemeLevel || null,
      nodalMinistryName: item.nodalMinistryName || item.ministry || null,
      tags: Array.isArray(item.tags) ? item.tags : 
            (item.tag ? [item.tag] : 
            (item.category ? [item.category] : [])),
      schemeCategory: Array.isArray(item.schemeCategory) ? item.schemeCategory :
                     Array.isArray(item.category) ? item.category :
                     (item.category ? [item.category] : []),
      detailedDescription_md: item.detailedDescription_md || item.description || item.details || '',
      eligibilityDescription_md: item.eligibilityDescription_md || item.eligibility || '',
      benefits: Array.isArray(item.benefits) ? item.benefits : 
               (item.benefit ? [item.benefit] : []),
      documents_required: Array.isArray(item.documents_required) ? item.documents_required :
                         Array.isArray(item.documents) ? item.documents :
                         (item.document ? [item.document] : []),
      applicationProcess: Array.isArray(item.applicationProcess) ? item.applicationProcess :
                         (item.application ? [item.application] : []),
      faqs: Array.isArray(item.faqs) ? item.faqs : [],
      references: Array.isArray(item.references) ? item.references : [],
      openDate: item.openDate || item.startDate || null,
      closeDate: item.closeDate || item.endDate || null,
    };

    // Validate required fields
    if (!scheme.schemeName || !scheme.schemeShortTitle) {
      return null;
    }

    // Fix level enum
    if (scheme.level) {
      const levelMap = {
        'central': 'Central',
        'state': 'State',
        'state/ut': 'State/ UT',
        'State/UT': 'State/ UT'
      };
      scheme.level = levelMap[scheme.level.toLowerCase()] || scheme.level;
    }

    // Fix nodalMinistryName structure
    if (scheme.nodalMinistryName && typeof scheme.nodalMinistryName === 'object') {
      if (scheme.nodalMinistryName.label) {
        scheme.nodalMinistryName = scheme.nodalMinistryName.label;
      } else if (typeof scheme.nodalMinistryName === 'string') {
        // Already a string, keep it
      } else {
        scheme.nodalMinistryName = JSON.stringify(scheme.nodalMinistryName);
      }
    }

    // Fix date formats
    if (scheme.openDate) {
      if (scheme.openDate === 'NaN-NaN-NaN' || scheme.openDate === 'Invalid Date') {
        scheme.openDate = null;
      } else if (typeof scheme.openDate === 'string') {
        const date = new Date(scheme.openDate);
        scheme.openDate = isNaN(date.getTime()) ? null : date;
      }
    }

    if (scheme.closeDate) {
      if (scheme.closeDate === 'NaN-NaN-NaN' || scheme.closeDate === 'Invalid Date') {
        scheme.closeDate = null;
      } else if (typeof scheme.closeDate === 'string') {
        const date = new Date(scheme.closeDate);
        scheme.closeDate = isNaN(date.getTime()) ? null : date;
      }
    }

    return scheme;
  } catch (error) {
    console.error('   Error transforming scheme:', error.message);
    return null;
  }
};

/**
 * Connect to MongoDB
 */
const connectDB = async () => {
  try {
    console.log('💾 Connecting to MongoDB...');
    await mongoose.connect(process.env.MONGODB_URL);
    console.log('✅ MongoDB Connected');
  } catch (error) {
    console.error('❌ Error connecting to MongoDB:', error);
    process.exit(1);
  }
};

/**
 * Apply post-processing queries
 */
const applyPostProcessing = async () => {
  console.log('🔧 Applying post-processing transformations...');
  
  try {
    // Use raw MongoDB collection to avoid Mongoose type casting issues
    const collection = Schemev2.collection;
    
    // First, fix invalid date strings (must be done before type conversion)
    // Use raw collection to avoid Mongoose trying to cast 'NaN-NaN-NaN' to Date
    const invalidDateResult = await collection.updateMany(
      { 
        $or: [
          { openDate: 'NaN-NaN-NaN' },
          { openDate: { $type: 'string', $regex: /^NaN/ } }
        ]
      },
      { $set: { openDate: null } }
    );
    if (invalidDateResult.modifiedCount > 0) {
      console.log(`   ✅ Fixed ${invalidDateResult.modifiedCount} invalid openDate values`);
    }

    const invalidCloseDateResult = await collection.updateMany(
      { 
        $or: [
          { closeDate: 'NaN-NaN-NaN' },
          { closeDate: { $type: 'string', $regex: /^NaN/ } }
        ]
      },
      { $set: { closeDate: null } }
    );
    if (invalidCloseDateResult.modifiedCount > 0) {
      console.log(`   ✅ Fixed ${invalidCloseDateResult.modifiedCount} invalid closeDate values`);
    }

    // Now fix dates that are valid strings (but not Date objects)
    // Only convert strings that match date format (yyyy-mm-dd)
    const openDateResult = await collection.updateMany(
      { 
        openDate: { 
          $type: 'string',
          $regex: /^\d{4}-\d{2}-\d{2}/
        }
      },
      [{ $set: { openDate: { $toDate: '$openDate' } } }]
    );
    if (openDateResult.modifiedCount > 0) {
      console.log(`   ✅ Converted ${openDateResult.modifiedCount} openDate strings to dates`);
    }

    const closeDateResult = await collection.updateMany(
      { 
        closeDate: { 
          $type: 'string',
          $regex: /^\d{4}-\d{2}-\d{2}/
        }
      },
      [{ $set: { closeDate: { $toDate: '$closeDate' } } }]
    );
    if (closeDateResult.modifiedCount > 0) {
      console.log(`   ✅ Converted ${closeDateResult.modifiedCount} closeDate strings to dates`);
    }

    // Fix nodalMinistryName if it's still an object
    const ministryResult = await Schemev2.updateMany(
      { 'nodalMinistryName.label': { $exists: true } },
      [{ $set: { nodalMinistryName: '$nodalMinistryName.label' } }]
    );
    if (ministryResult.modifiedCount > 0) {
      console.log(`   ✅ Fixed ${ministryResult.modifiedCount} nodalMinistryName structures`);
    }

    console.log('✅ Post-processing complete');
  } catch (error) {
    console.error('❌ Error in post-processing:', error.message);
    // Don't fail the entire process if post-processing has issues
  }
};

/**
 * Main seed function
 */
const seedSchemes = async () => {
  try {
    console.log('🌱 Starting scheme seeding process...\n');

    // Load dataset
    const rawData = await loadDataset();
    
    if (!rawData || !Array.isArray(rawData)) {
      console.error('❌ Invalid dataset format. Expected an array.');
      process.exit(1);
    }

    console.log(`📊 Total items in dataset: ${rawData.length}`);

    // Transform data
    console.log('🔄 Transforming data to match schema...');
    const transformedSchemes = [];
    const seenTitles = new Set();

    for (let i = 0; i < rawData.length; i++) {
      if (CONFIG.LIMIT && transformedSchemes.length >= CONFIG.LIMIT) {
        break;
      }

      const transformed = transformScheme(rawData[i]);
      
      if (transformed) {
        // Check for duplicates
        if (!seenTitles.has(transformed.schemeShortTitle)) {
          seenTitles.add(transformed.schemeShortTitle);
          transformedSchemes.push(transformed);
        }
      }

      if ((i + 1) % 100 === 0) {
        process.stdout.write(`\r   Processed: ${i + 1}/${rawData.length}`);
      }
    }

    console.log(`\n✅ Transformed: ${transformedSchemes.length} valid schemes`);
    console.log(`   Skipped: ${rawData.length - transformedSchemes.length} (invalid/duplicates)\n`);

    if (transformedSchemes.length === 0) {
      console.log('⚠️  No valid schemes to import. Exiting...');
      process.exit(0);
    }

    // Connect to database
    await connectDB();

    // Clear existing data if configured
    if (CONFIG.CLEAR_EXISTING) {
      console.log('🗑️  Clearing existing schemes...');
      await Schemev2.deleteMany({});
      console.log('✅ Cleared existing data\n');
    }

    // Import schemes in batches
    console.log('📊 Importing schemes...');
    let imported = 0;
    let errors = 0;

    for (let i = 0; i < transformedSchemes.length; i += CONFIG.BATCH_SIZE) {
      const batch = transformedSchemes.slice(i, i + CONFIG.BATCH_SIZE);
      
      try {
        await Schemev2.insertMany(batch, { ordered: false });
        imported += batch.length;
        const progress = Math.round((imported / transformedSchemes.length) * 100);
        process.stdout.write(`\r   [${'█'.repeat(Math.floor(progress / 5))}${'░'.repeat(20 - Math.floor(progress / 5))}] ${progress}% (${imported}/${transformedSchemes.length})`);
      } catch (error) {
        // Handle duplicate key errors
        if (error.code === 11000) {
          // Count how many were actually inserted
          const inserted = await Schemev2.countDocuments({
            schemeShortTitle: { $in: batch.map(s => s.schemeShortTitle) }
          });
          imported += inserted;
        } else {
          errors += batch.length;
          console.error(`\n   ⚠️  Error inserting batch: ${error.message}`);
        }
      }
    }

    console.log(`\n✅ Successfully imported ${imported} schemes`);
    if (errors > 0) {
      console.log(`⚠️  ${errors} schemes failed to import`);
    }

    // Apply post-processing
    console.log();
    await applyPostProcessing();

    // Summary
    const finalCount = await Schemev2.countDocuments();
    console.log('\n📈 Summary:');
    console.log(`   - Total in dataset: ${rawData.length}`);
    console.log(`   - Valid schemes: ${transformedSchemes.length}`);
    console.log(`   - Imported: ${imported}`);
    console.log(`   - Total in database: ${finalCount}`);
    console.log(`   - Errors: ${errors}\n`);

    console.log('✅ Seeding complete!');
    process.exit(0);
  } catch (error) {
    console.error('❌ Error seeding schemes:', error);
    process.exit(1);
  }
};

// Run the seed function
seedSchemes();

