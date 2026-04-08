import Schemev2 from "../models/schemev2.model.js";
import User from "../models/user.model.js";

const CATEGORY_KEYWORD_MAP = {
    'Education': ['education', 'scholarship', 'student', 'course', 'skill', 'training'],
    'Healthcare': ['health', 'medical', 'disease', 'treatment', 'hospital', 'nursing', 'ayurveda'],
    'Women Empowerment': ['women', 'girl', 'maternity', 'harassment', 'widow'],
    'Employment': ['job', 'employment', 'unemployment', 'wage', 'labor', 'worker'],
    'Housing': ['housing', 'house', 'home', 'rent', 'construction', 'property'],
    'Agriculture': ['agriculture', 'farmer', 'farm', 'crop', 'livestock', 'irrigation', 'soil'],
    'Skill Development': ['skill', 'training', 'vocational', 'apprenticeship', 'development'],
    'Transportation': ['transport', 'vehicle', 'auto', 'taxi', 'bus', 'fuel'],
    'Energy': ['energy', 'solar', 'power', 'electricity', 'renewable'],
    'Digital India': ['digital', 'internet', 'telecom', 'broadband', 'online'],
    'Rural Development': ['rural', 'village', 'development', 'infrastructure', 'farming'],

    // Categories used in SchemeSearch dropdown
    'Women and Child': ['women', 'woman', 'girl', 'child', 'children', 'maternity', 'widow'],
    'Utility & Sanitation': ['utility', 'sanitation', 'toilet', 'water', 'hygiene', 'clean'],
    'Travel & Tourism': ['travel', 'tourism', 'tourist', 'pilgrimage', 'trip'],
    'Transport & Infrastructure Sports & Culture': ['transport', 'infrastructure', 'sports', 'culture', 'stadium', 'road'],
    'Social welfare & Empowerment': ['social', 'welfare', 'empowerment', 'pension', 'support'],
    'Skills & Employment': ['skill', 'training', 'employment', 'job', 'worker', 'entrepreneur'],
    'Science, IT & Communications': ['science', 'technology', 'it', 'digital', 'communication', 'telecom'],
    'Public Safety,Law & Justice': ['safety', 'law', 'justice', 'legal', 'security', 'police'],
    'Housing & Shelter': ['housing', 'house', 'home', 'shelter', 'rent', 'construction'],
    'Health & Wellness': ['health', 'wellness', 'medical', 'hospital', 'treatment', 'medicine'],
    'Education & Learning': ['education', 'learning', 'scholarship', 'student', 'school', 'college'],
    'Business & Entrepreneurship': ['business', 'entrepreneurship', 'startup', 'msme', 'enterprise', 'trade'],
    'Banking, Financial Services and Insurance': ['banking', 'financial', 'finance', 'insurance', 'credit', 'loan'],
    'Agriculture,Rural & Environment': ['agriculture', 'rural', 'environment', 'farmer', 'farm', 'climate']
};

const escapeRegex = (text = '') => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const getCategoryTerms = (categoryValue = '') => {
    const normalized = String(categoryValue).trim();
    if (!normalized) {
        return [];
    }

    if (CATEGORY_KEYWORD_MAP[normalized]) {
        return CATEGORY_KEYWORD_MAP[normalized];
    }

    // Fallback: derive keywords from category text so unknown categories still filter.
    return normalized
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .map((term) => term.trim())
        .filter((term) => term.length > 2);
};

const getAllSchemes = async (req, res) => {
    try {
        const { page = 1, limit = 9 } = req.query;
        const options = {
            page: parseInt(page),
            limit: parseInt(limit),
            sort: { createdAt: -1 }
        };

        const schemes = await Schemev2.paginate({}, options);
        res.status(200).json({
            schemes: schemes.docs,
            totalPages: schemes.totalPages,
            currentPage: schemes.page,
            totalSchemes: schemes.totalDocs
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

const getSchemeById = async (req, res) => {
    try {
        const scheme = await Schemev2.findById(req.params.id);
        res.status(200).json(scheme);
    }
    catch (error) {
        res.status(404).json({ message: "Scheme not found" });
    }
};

const getSchemeByCategory = async (req, res) => {
    try {
        const { page = 1, limit = 9 } = req.query;
        const options = {
            page: parseInt(page),
            limit: parseInt(limit),
            sort: { createdAt: -1 }
        };

        const schemes = await Schemev2.paginate(
            { schemeCategory: req.params.category },
            options
        );
        res.status(200).json({
            schemes: schemes.docs,
            totalPages: schemes.totalPages,
            currentPage: schemes.page,
            totalSchemes: schemes.totalDocs
        });
    } catch (error) {
        res.status(404).json({ message: "Category not found" });
    }
};

const getFilteredSchemes = async (req, res) => {
    try {
        const { page = 1, limit = 9 } = req.query;
        const { search, openDate, closeDate, state, nodalMinistryName, level, category, tags, schemeName } = req.query;

        const filter = {};
        const andConditions = [];

        if (search) {
            andConditions.push({ $or: [
                { state: { $eq: search } },
                { nodalMinistryName: { $regex: search, $options: 'i' } },
                { schemeName: { $regex: search, $options: 'i' } },
                { tags: { $in: [search] } },
                { level: { $eq: search } },
                { schemeCategory: { $regex: search, $options: 'i' } },
                { detailedDescription_md: { $regex: search, $options: 'i' } },
            ]});
        }

        if (openDate || closeDate) {
            const dateConds = [];
            if (openDate) dateConds.push({ openDate: { $gte: new Date(openDate) } });
            if (closeDate) dateConds.push({ closeDate: { $lte: new Date(closeDate) } });
            dateConds.push({ openDate: null });
            dateConds.push({ closeDate: null });
            andConditions.push({ $or: dateConds });
        }

        if (schemeName) {
            andConditions.push({ $or: [
                { schemeName: { $regex: schemeName, $options: 'i' } },
                { schemeShortTitle: { $regex: schemeName, $options: 'i' } },
            ]});
        }

        if (state) filter.state = state;
        if (nodalMinistryName) filter.nodalMinistryName = nodalMinistryName;
        if (level) filter.level = level;

        if (category) {
            const normalizedCategory = String(category).trim();

            // If the full category exists in map, treat it as a single category label.
            // Otherwise keep support for comma-separated category filters.
            const categoryValues = CATEGORY_KEYWORD_MAP[normalizedCategory]
                ? [normalizedCategory]
                : normalizedCategory.split(',').map((item) => item.trim()).filter(Boolean);

            const categoryTerms = [...new Set(categoryValues.flatMap((item) => getCategoryTerms(item)))];
            const categoryRegexes = categoryValues.map((item) => new RegExp(escapeRegex(item), 'i'));

            const categoryOrConditions = [];

            if (categoryTerms.length > 0) {
                categoryOrConditions.push({ tags: { $in: categoryTerms } });

                const textSearchTerms = categoryTerms.filter((term) => term.length > 3);
                if (textSearchTerms.length > 0) {
                    const categoryTermsRegex = new RegExp(
                        textSearchTerms.map((term) => escapeRegex(term)).join('|'),
                        'i'
                    );
                    categoryOrConditions.push({ schemeName: categoryTermsRegex });
                    categoryOrConditions.push({ schemeShortTitle: categoryTermsRegex });
                }
            }

            if (categoryValues.length > 0) {
                categoryOrConditions.push({ schemeCategory: { $in: categoryValues } });
                categoryOrConditions.push({ schemeName: { $in: categoryRegexes } });
                categoryOrConditions.push({ schemeShortTitle: { $in: categoryRegexes } });
            }

            if (categoryOrConditions.length > 0) {
                andConditions.push({ $or: categoryOrConditions });
            }
        }

        if (tags) {
            const tagsArray = tags.split(',');
            filter.tags = { $in: tagsArray };
        }

        if (andConditions.length > 0) {
            filter.$and = andConditions;
        }

        const options = {
            page: parseInt(page),
            limit: parseInt(limit),
            sort: { createdAt: -1 }
        };

        const schemes = await Schemev2.paginate(filter, options);
        res.status(200).json({
            schemes: schemes.docs,
            totalPages: schemes.totalPages,
            currentPage: schemes.page,
            totalSchemes: schemes.totalDocs
        });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Error retrieving filtered schemes", error: err });
    }
};

// save favorite schemes

const saveFavoriteSchemes = async (req, res) => {
    try {
        // Get the logged-in user's ID from the request
        const userId = req.user._id;

        // Get the scheme IDs from the request body
        const schemeId = req.body.schemeId;

        // Find the user by ID and update the favorites array
        const user = await User.findByIdAndUpdate(
            userId,
            { $push: { favorites: schemeId } },
            { new: true }
        );

        // Return a success response
        res.status(200).json({ message: "Favorite schemes saved successfully" });
    } catch (error) {
        // Handle errors
        console.error("Error saving favorite schemes:", error);
        res.status(500).json({ message: "Error saving favorite schemes" });
    }
};

const removeFavoriteSchemes = async (req, res) => {
    try {
        const userId = req.user._id;
        const { id } = req.params; // Change to use params instead of body

        const user = await User.findByIdAndUpdate(
            userId,
            { $pull: { favorites: id } },
            { new: true }
        );

        if (!user) {
            return res.status(404).json({ message: "User not found" });
        }

        res.status(200).json({
            success: true,
            message: "Scheme removed from favorites"
        });
    } catch (error) {
        console.error("Error removing favorite scheme:", error);
        res.status(500).json({
            success: false,
            message: "Error removing favorite scheme"
        });
    }
};

const getFavoriteSchemes = async (req, res) => {
    try {
        const userId = req.user._id;
        const user = await User.findById(userId).populate('favorites');
        if (!user) return res.status(404).json({ message: "User not found" });
        res.status(200).json(user.favorites);
    } catch (error) {
        console.error("Error retrieving favorite schemes:", error);
        res.status(500).json({ message: "Error retrieving favorite schemes" });
    }
};

export { getAllSchemes, getSchemeById, getSchemeByCategory, getFilteredSchemes, saveFavoriteSchemes, removeFavoriteSchemes, getFavoriteSchemes };