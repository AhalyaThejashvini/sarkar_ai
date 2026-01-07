import dotenv from "dotenv";
import connectDB from "./db/index.js";
import app from "./app.js";

// dotenv.config();
// import dotenv from "dotenv";
dotenv.config({ path: "./.env" }); // explicitly points to root .env

console.log("Mongo URL:", process.env.MONGODB_URL);




connectDB()
.then(
    app.listen(process.env.PORT || 5000, () => {
        console.log("Server running on port 5000");
    })
)
.catch(
    (error) => console.error("Error connecting to MongoDB", error)
)