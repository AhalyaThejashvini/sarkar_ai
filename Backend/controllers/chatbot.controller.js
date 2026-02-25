import { generateSchemeResponse, generateGenericResponse } from "../services/chatbot.service.js";
import Schemev2 from "../models/schemev2.model.js";

export const getSchemeResponse = async (req, res) => {
    console.log('CHATBOT REQUEST BODY:', req.body);
    try {
        const { schemeId, question, language = 'en' } = req.body;

        if (!question) {
            return res.status(400).json({ 
                message: 'Question is required' 
            });
        }

        let responseText;

        if (schemeId) {
            const scheme = await Schemev2.findById(schemeId);
            if (!scheme) {
                return res.status(404).json({ 
                    message: 'Scheme not found' 
                });
            }

            responseText = await generateSchemeResponse(scheme, question, language);
        } else {
            // No schemeId provided — generate a generic response
            responseText = await generateGenericResponse(question, language);
        }

        res.status(200).json({ response: responseText });
    } catch (error) {
        console.error('Error in chatbot response:', error);
        res.status(500).json({ 
            message: 'Error generating response' 
        });
    }
};
