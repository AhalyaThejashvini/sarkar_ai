import mongoose from "mongoose";

const connectDB = async () => {
  try {
    console.log("Attempting to connect to MongoDB...");
    console.log("MongoDB URL:", process.env.MONGODB_URL ? "Found" : "Not found");
    
    await mongoose.connect(process.env.MONGODB_URL);
      
    console.log("✅ MongoDB Connected...");
  } catch (error) {
    console.error("❌ Error connecting to MongoDB\n", error);
    process.exit(1);
  }
};

export default connectDB;
