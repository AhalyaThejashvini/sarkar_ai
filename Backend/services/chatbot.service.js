import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from 'dotenv';
dotenv.config();

console.log('Gemini API Key loaded:', process.env.GEMINI_API_KEY ? 'YES (hidden)' : 'NO - NOT SET');

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const languageMap = {
    en: 'English',
    hi: 'Hindi',
    pa: 'Punjabi',
    bn: 'Bengali',
    te: 'Telugu',
    ta: 'Tamil',
    gu: 'Gujarati',
    mr: 'Marathi',
    kn: 'Kannada',
    ml: 'Malayalam',
    or: 'Odia',
    ur: 'Urdu',
    sa: 'Sanskrit',
    ne: 'Nepali',
    sd: 'Sindhi',
    ks: 'Kashmiri'
};

export const generateSchemeResponse = async (scheme, question, language = 'en') => {
    try {
        const model = genAI.getGenerativeModel({ model: "gemini-flash-latest" });

        // Create a context-aware prompt with language instruction
        const prompt = `
        Given this government scheme:
        
        Basic Information:
        - Name: ${scheme.schemeName}
        - Short Title: ${scheme.schemeShortTitle}
        - Level: ${scheme.level}
        - State: ${scheme.state || 'Not specified'}
        - Ministry: ${scheme.nodalMinistryName?.label || 'Not specified'}
        
        Timeline:
        - Open Date: ${scheme.openDate ? new Date(scheme.openDate).toLocaleDateString() : 'Not specified'}
        - Close Date: ${scheme.closeDate ? new Date(scheme.closeDate).toLocaleDateString() : 'Not specified'}
        
        Categories and Tags:
        - Categories: ${scheme.schemeCategory?.join(', ')}
        - Tags: ${scheme.tags?.join(', ')}
        
        Detailed Information:
        - Description: ${scheme.detailedDescription_md}
        - Eligibility Criteria: ${scheme.eligibilityDescription_md}
        
        Application Process:
        ${scheme.applicationProcess?.map(process => `
            Mode: ${process.mode}
            Process: ${JSON.stringify(process.process)}
        `).join('\n')}
        
        Required Documents:
        ${scheme.documents_required?.map(doc => JSON.stringify(doc)).join('\n')}
        
        Benefits:
        ${scheme.benefits?.map(benefit => JSON.stringify(benefit)).join('\n')}
        
        References:
        ${scheme.references?.map(ref => `- ${ref.title}: ${ref.url}`).join('\n')}
        
        FAQs:
        ${scheme.faqs?.map(faq => `Q: ${faq.question}\nA: ${faq.answer}`).join('\n')}

        User Question: ${question}

        Please provide a clear, concise, and helpful response about this scheme.
        If the question is about eligibility, reference the specific criteria.
        If the question is about application process, provide step-by-step guidance.
        If the question is about documents, list the specific requirements.
        If the question is about benefits, explain them clearly.
        If the question is about deadlines, mention both open and close dates if available.

        Important: 
        1. Respond in ${languageMap[language] || 'English'} language
        2. Keep the response focused and relevant to the question
        3. If information is not available, clearly state that
        4. For dates, mention if they are current or past
        `;

        const result = await model.generateContent(prompt);
        const response = await result.response;
        return response.text();
    } catch (error) {
        const errorMsg = error.message || String(error);
        console.error('Error generating chatbot response:', errorMsg);

        // Check if it's a quota error (free tier limit exceeded)
        if (errorMsg.includes('429') || errorMsg.includes('quota') || errorMsg.includes('Quota exceeded')) {
            return `I'm currently experiencing high demand on the AI service. However, here's the key information about this scheme:\n\n**${scheme.schemeName}** (${scheme.schemeShortTitle})\nMinistry: ${scheme.nodalMinistryName?.label || 'Not specified'}\nState: ${scheme.state || 'Not specified'}\n\nFor detailed information, please visit the scheme page or contact the nodal ministry directly.`;
        }

        return "I apologize, but I'm having trouble processing your question. Please try asking in a different way or contact support for assistance.";
    }
};

export const generateGenericResponse = async (question, language = 'en') => {
    try {
        const model = genAI.getGenerativeModel({ model: "gemini-flash-latest" });

        const prompt = `You are an assistant that answers questions about government schemes in India. Provide a concise, helpful answer to the user's question below. If the user asks for specific scheme details, mention that no specific scheme context was provided and offer guidance on how to find relevant schemes (search by category, eligibility, or state).\n\nUser question: ${question}\n\nRespond in ${languageMap[language] || 'English'}.`;

        const result = await model.generateContent(prompt);
        const response = await result.response;
        return response.text();
    } catch (error) {
        const errorMsg = error.message || String(error);
        console.error('Error generating generic chatbot response:', errorMsg);

        // Check if it's a quota error (free tier limit exceeded)
        if (errorMsg.includes('429') || errorMsg.includes('quota') || errorMsg.includes('Quota exceeded')) {
            return `I'm currently experiencing high demand on the AI service due to free tier usage limits. However, here are some general tips:\n\n📚 **Tips for Finding Government Schemes:**\n1. Browse schemes by **category** (education, healthcare, employment, etc.)\n2. Filter by your **state** to see location-specific schemes\n3. Check **eligibility criteria** carefully before applying\n4. Use the search feature to find schemes by keywords\n\nPlease try your query again in a few moments, or explore the schemes using the filters above!`;
        }

        return "I apologize, but I'm having trouble processing your question. Please try asking in a different way or contact support for assistance.";
    }
};
