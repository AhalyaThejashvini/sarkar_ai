import React from "react";

const isRichTextNode = (value) => value && typeof value === 'object' && 'type' in value;

const renderPlainText = (value) => {
    if (value === null || value === undefined) return null;

    if (typeof value === 'string' || typeof value === 'number') {
        return value;
    }

    if (Array.isArray(value)) {
        return value
            .map((item) => renderPlainText(item))
            .filter(Boolean)
            .join(' ');
    }

    if (typeof value === 'object') {
        return value.text || value.title || value.document || value.description || value.mode || value.process || value.answer || '';
    }

    return '';
};

const renderRichTextChildren = (children) => {
    if (!children) return null;

    return children.map((child, index) => {
        const style = {};
        const text = child.text || '';

        if (child.bold) style.fontWeight = 'bold';
        if (child.underline) style.textDecoration = 'underline';
        if (child.italic) style.fontStyle = 'italic';

        if (child.type === "link") {
            return (
                <a
                    href={child.link}
                    key={index}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                >
                    {renderRichTextChildren(child.children)}
                </a>
            );
        }

        return (
            <span key={index} style={style}>
                {text || ''}
            </span>
        );
    });
};

const TableComponent = ({ children }) => (
    <div className="overflow-x-auto my-4">
        <table className="min-w-full border-collapse border border-gray-300">
            <tbody>
                {children.map((row, index) => (
                    <tr key={index} className="border-b border-gray-300">
                        {row.children.map((cell, cellIndex) => (
                            <td key={cellIndex} className="p-2 border-r border-gray-300">
                                {renderRichTextChildren(cell.children)}
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    </div>
);

const RenderRichContent = ({ content }) => {
    if (!content) return null;

    return content.map((item, index) => {
        switch (item.type) {
            case "paragraph":
                return <p key={index} className="my-2">{renderRichTextChildren(item.children)}</p>;
            case "block_quote":
                return <blockquote key={index} className="border-l-4 border-gray-300 pl-4 my-4">{renderRichTextChildren(item.children)}</blockquote>;
            case "table":
                return <TableComponent key={index} children={item.children} />;
            case "ol_list":
            case "ul_list":
                return <div key={index} className="my-2">{renderRichTextChildren(item.children)}</div>;
            default:
                return <div key={index} className="my-2">{renderRichTextChildren(item.children)}</div>;
        }
    });
};

const RenderStructuredItem = ({ item, index }) => {
    if (typeof item === 'string' || typeof item === 'number') {
        return <li key={index} className="mb-3">{renderPlainText(item)}</li>;
    }

    if (isRichTextNode(item)) {
        return <RenderRichContent key={index} content={[item]} />;
    }

    if (item && typeof item === 'object') {
        const title = item.title || item.document || item.mode || item.question || item.name;
        const description = item.description || item.process || item.answer;

        return (
            <li key={index} className="mb-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                {title && <div className="font-semibold text-gray-900">{renderPlainText(title)}</div>}
                {description && (
                    <div className="mt-2 text-gray-600 space-y-2">
                        {Array.isArray(description)
                            ? description.map((line, lineIndex) => (
                                <p key={lineIndex}>{renderPlainText(line)}</p>
                            ))
                            : renderPlainText(description)}
                    </div>
                )}
                {!title && !description && <pre className="whitespace-pre-wrap text-sm text-gray-600">{JSON.stringify(item, null, 2)}</pre>}
            </li>
        );
    }

    return null;
};

const DisplayFormatted = ({ benefitsData }) => {
    if (!benefitsData || (Array.isArray(benefitsData) && benefitsData.length === 0)) {
        return <div>No data available</div>;
    }

    const items = Array.isArray(benefitsData) ? benefitsData : [benefitsData];

    if (items.every((item) => typeof item === 'string' || typeof item === 'number')) {
        return (
            <ul className="list-disc pl-6 space-y-2 text-gray-600">
                {items.map((item, index) => (
                    <li key={index}>{renderPlainText(item)}</li>
                ))}
            </ul>
        );
    }

    return (
        <div className="prose max-w-none">
            <ul className="space-y-3 list-none p-0 m-0">
                {items.map((item, index) => (
                    <RenderStructuredItem key={index} item={item} index={index} />
                ))}
            </ul>
        </div>
    );
};

export default DisplayFormatted;