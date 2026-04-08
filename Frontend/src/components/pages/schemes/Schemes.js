import { useState, useEffect, useCallback } from 'react';
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Search } from 'lucide-react';
import SchemeSearch from "./SchemeSearch";
import SchemeCard from "../../common/schemeCard/SchemeCard";
import { getFilteredSchemes, getAllSchemes } from '../../../services/schemes/schemeService';
import Pagination from '../../common/pagination/Pagination';

const FILTER_KEYS = [
    'search',
    'schemeName',
    'openDate',
    'closeDate',
    'state',
    'nodalMinistryName',
    'level',
    'category',
    'gender',
    'incomeGroup'
];

const cleanFilters = (rawFilters = {}) => {
    return Object.fromEntries(
        Object.entries(rawFilters).filter(([_, value]) =>
            value !== undefined && value !== null && String(value).trim() !== ''
        )
    );
};

const parseFiltersFromQuery = (search) => {
    const params = new URLSearchParams(search);
    const parsed = {};

    const category = params.get('category') || params.get('cat');
    if (category) {
        parsed.category = category;
    }

    FILTER_KEYS.forEach((key) => {
        if (key === 'category') {
            return;
        }

        const value = params.get(key);
        if (value) {
            parsed[key] = value;
        }
    });

    return parsed;
};

const buildQueryString = (filters = {}, page = 1) => {
    const params = new URLSearchParams();
    const normalizedFilters = cleanFilters(filters);

    Object.entries(normalizedFilters).forEach(([key, value]) => {
        params.set(key, value);
    });

    if (page > 1) {
        params.set('page', String(page));
    }

    return params.toString();
};

const Schemes = () => {
    const [schemes, setSchemes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalSchemes, setTotalSchemes] = useState(0);
    const [filters, setFilters] = useState({});
    const [error, setError] = useState(null);
    const location = useLocation();
    const navigate = useNavigate();

    const fetchSchemes = async (page, activeFilters = {}) => {
        try {
            setLoading(true);
            setError(null);
            let data;

            if (Object.keys(activeFilters).length > 0) {
                data = await getFilteredSchemes(activeFilters, page);
            } else {
                data = await getAllSchemes(page);
            }

            setSchemes(data.schemes);
            setTotalPages(data.totalPages);
            setCurrentPage(data.currentPage);
            setTotalSchemes(data.totalSchemes);
        } catch (error) {
            setError("Failed to fetch schemes. Please try again.");
            console.error('Error fetching schemes:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const activeFilters = parseFiltersFromQuery(location.search);
        const parsedPage = parseInt(params.get('page') || '1', 10);
        const page = Number.isNaN(parsedPage) || parsedPage < 1 ? 1 : parsedPage;

        setFilters(activeFilters);
        setCurrentPage(page);
        fetchSchemes(page, activeFilters);
    }, [location.search]);

    const handlePageChange = (page) => {
        const queryString = buildQueryString(filters, page);
        const nextSearch = queryString ? `?${queryString}` : '';

        if (nextSearch === location.search) {
            setCurrentPage(page);
            fetchSchemes(page, filters);
        } else {
            navigate({ pathname: '/schemes', search: nextSearch });
        }

        window.scrollTo(0, 0);
    };

    const handleSearch = (newFilters) => {
        const activeFilters = cleanFilters(newFilters);
        const queryString = buildQueryString(activeFilters, 1);
        const nextSearch = queryString ? `?${queryString}` : '';

        if (nextSearch === location.search) {
            setFilters(activeFilters);
            setCurrentPage(1);
            fetchSchemes(1, activeFilters);
        } else {
            navigate({ pathname: '/schemes', search: nextSearch });
        }
    };

    const schemesCountText = totalSchemes > 0
        ? `Showing ${(currentPage - 1) * 9}-${currentPage * 9} of ${totalSchemes} schemes`
        : '';

    // ... rest of your JSX stays exactly the same

    return (
        <div className="bg-gray-100 min-h-screen">
            <section className="container mx-auto py-12">
                <h1 className="text-4xl font-bold pt-10 mb-8 text-center">Find Schemes for You</h1>
                <div className="bg-gray-200 rounded-lg shadow-md sm:px-6 sm:py-10 mb-8">
                    <SchemeSearch onSearch={handleSearch} initialFilters={filters} />
                </div>

                {!loading && schemesCountText && (
                    <p className="text-gray-600 mb-4">{schemesCountText}</p>
                )}

                {loading && (
                    <div className="text-center py-8">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#74B83E]"></div>
                        <p className="mt-2 text-xl">Loading schemes...</p>
                    </div>
                )}

                {error && (
                    <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-8" role="alert">
                        <p>{error}</p>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {schemes.map((scheme) => (
                        <Link
                            to={`/scheme/${scheme._id}`}
                            key={scheme._id}
                        >

                            <SchemeCard
                                key={scheme._id}
                                scheme={scheme}
                            />
                        </Link>
                    ))}
                </div>

                {!loading && schemes.length > 0 && (
                    <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        onPageChange={handlePageChange}
                    />
                )}

                {schemes.length === 0 && !loading && (
                    <div className="text-center py-8">
                        <Search size={48} className="text-gray-400 mx-auto mb-4" />
                        <p className="text-xl text-gray-600">
                            No schemes found. Try adjusting your search filters.
                        </p>
                    </div>
                )}
            </section>
        </div>
    );
};

export default Schemes;
