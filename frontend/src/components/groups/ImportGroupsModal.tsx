import React, { useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { XMarkIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { GroupsApi } from '../../api/client';
import { useTranslation } from 'react-i18next';

interface ImportGroupsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onImportComplete: () => void;
}

interface GroupCandidate {
    whatsapp_chat_id: string;
    name: string;
    is_in_db: boolean;
    participants_count: number;
}

export const ImportGroupsModal: React.FC<ImportGroupsModalProps> = ({ isOpen, onClose, onImportComplete }) => {
    const { t } = useTranslation();
    const [candidates, setCandidates] = useState<GroupCandidate[]>([]);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isLoading, setIsLoading] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            fetchCandidates();
        }
    }, [isOpen]);

    const fetchCandidates = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await GroupsApi.getCandidates();
            setCandidates(data);
        } catch (err) {
            setError('Failed to load groups from WhatsApp');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleImport = async () => {
        setIsImporting(true);
        const groupsToImport = candidates
            .filter(c => selectedIds.has(c.whatsapp_chat_id))
            .map(c => ({ whatsapp_chat_id: c.whatsapp_chat_id, name: c.name }));

        try {
            await GroupsApi.batchImport(groupsToImport);
            onImportComplete();
            onClose();
        } catch (err) {
            setError('Failed to import groups');
            console.error(err);
        } finally {
            setIsImporting(false);
        }
    };

    const toggleSelection = (id: string) => {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedIds(newSelected);
    };

    const filteredCandidates = candidates.filter(c =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-50" onClose={onClose}>
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-y-auto">
                    <div className="flex min-h-full items-center justify-center p-4">
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 scale-95"
                            enterTo="opacity-100 scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 scale-100"
                            leaveTo="opacity-0 scale-95"
                        >
                            <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-slate-800 p-6 text-left align-middle shadow-xl transition-all border border-slate-700">
                                <div className="flex justify-between items-center mb-6">
                                    <Dialog.Title as="h3" className="text-xl font-semibold text-white">
                                        {t('Import WhatsApp Groups')}
                                    </Dialog.Title>
                                    <button onClick={onClose} className="text-slate-400 hover:text-white">
                                        <XMarkIcon className="h-6 w-6" />
                                    </button>
                                </div>

                                {/* Search */}
                                <div className="mb-4 relative">
                                    <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-3 text-slate-400" />
                                    <input
                                        type="text"
                                        placeholder={t('Search groups...')}
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                    />
                                </div>

                                {/* List */}
                                <div className="h-96 overflow-y-auto border border-slate-700 rounded-lg bg-slate-900/50 p-2 space-y-1">
                                    {isLoading ? (
                                        <div className="flex justify-center items-center h-full text-slate-400">
                                            Loading...
                                        </div>
                                    ) : error ? (
                                        <div className="flex justify-center items-center h-full text-red-400">
                                            {error}
                                        </div>
                                    ) : filteredCandidates.length === 0 ? (
                                        <div className="flex justify-center items-center h-full text-slate-400">
                                            No groups found
                                        </div>
                                    ) : (
                                        filteredCandidates.map((group) => (
                                            <div
                                                key={group.whatsapp_chat_id}
                                                className={`flex items-center p-3 rounded-lg cursor-pointer transition-colors ${group.is_in_db
                                                    ? 'opacity-50 cursor-not-allowed bg-slate-800/50'
                                                    : 'hover:bg-slate-800'
                                                    }`}
                                                onClick={() => !group.is_in_db && toggleSelection(group.whatsapp_chat_id)}
                                            >
                                                <div className="flex-shrink-0 mr-3">
                                                    <input
                                                        type="checkbox"
                                                        checked={group.is_in_db || selectedIds.has(group.whatsapp_chat_id)}
                                                        disabled={group.is_in_db}
                                                        className="h-5 w-5 rounded border-slate-600 bg-slate-700 text-primary-600 focus:ring-primary-500"
                                                        readOnly
                                                    />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium text-white truncate">
                                                        {group.name}
                                                    </p>
                                                    <p className="text-xs text-slate-400 truncate">
                                                        {group.whatsapp_chat_id}
                                                    </p>
                                                </div>
                                                {group.is_in_db && (
                                                    <span className="text-xs text-green-400 font-medium px-2 py-1 bg-green-400/10 rounded">
                                                        Imported
                                                    </span>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>

                                {/* Footer */}
                                <div className="mt-6 flex justify-between items-center">
                                    <div className="text-sm text-slate-400">
                                        {selectedIds.size} selected
                                    </div>
                                    <div className="space-x-3">
                                        <button
                                            onClick={onClose}
                                            className="px-4 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                                        >
                                            {t('Cancel')}
                                        </button>
                                        <button
                                            onClick={handleImport}
                                            disabled={selectedIds.size === 0 || isImporting}
                                            className="px-4 py-2 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {isImporting ? 'Importing...' : t('Import Selected')}
                                        </button>
                                    </div>
                                </div>
                            </Dialog.Panel>
                        </Transition.Child>
                    </div>
                </div>
            </Dialog>
        </Transition>
    );
};
