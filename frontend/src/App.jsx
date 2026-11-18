import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ConnectRepoPage from './pages/ConnectRepoPage';
import DashboardPage from './pages/DashboardPage';
import AskMemoryPage from './pages/AskMemoryPage';
import DecisionExplorerPage from './pages/DecisionExplorerPage';
import PRIntelligencePage from './pages/PRIntelligencePage';
import apiService from './services/api';
import { X, Loader2 } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [repositories, setRepositories] = useState([]);
  const [currentRepo, setCurrentRepo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);

  const fetchRepositories = async () => {
    try {
      const repos = await apiService.listRepositories();
      setRepositories(repos);
      if (repos.length > 0 && !currentRepo) {
        setCurrentRepo(repos[0]);
      }
    } catch (err) {
      console.error('Error fetching repositories:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  const handleConnected = (newRepo) => {
    setRepositories((prev) => {
      const exists = prev.find((r) => r.id === newRepo.id);
      if (exists) return prev.map((r) => (r.id === newRepo.id ? newRepo : r));
      return [newRepo, ...prev];
    });
    setCurrentRepo(newRepo);
    setActiveTab('dashboard');
    setIsConnectModalOpen(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <div className="flex items-center space-x-3">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
          <span className="text-sm font-medium">Starting DecisionTrail...</span>
        </div>
      </div>
    );
  }

  // If no repositories exist yet, show the connect page directly
  if (repositories.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col justify-center">
        <ConnectRepoPage onConnected={handleConnected} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500/30 selection:text-indigo-200">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentRepo={currentRepo}
        repositories={repositories}
        onSelectRepo={(repo) => setCurrentRepo(repo)}
        onOpenConnectModal={() => setIsConnectModalOpen(true)}
      />

      <main className="flex-1 pb-16">
        {activeTab === 'dashboard' && (
          <DashboardPage
            currentRepo={currentRepo}
            onNavigate={(tab) => setActiveTab(tab)}
            onRefreshRepo={fetchRepositories}
          />
        )}
        {activeTab === 'ask' && <AskMemoryPage currentRepo={currentRepo} />}
        {activeTab === 'decisions' && <DecisionExplorerPage currentRepo={currentRepo} />}
        {activeTab === 'pr' && <PRIntelligencePage currentRepo={currentRepo} />}
      </main>

      {/* Connect Repo Modal */}
      {isConnectModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="relative w-full max-w-3xl">
            <button
              onClick={() => setIsConnectModalOpen(false)}
              className="absolute right-4 top-4 z-20 text-slate-400 hover:text-white p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
            <ConnectRepoPage
              onConnected={handleConnected}
              isModal={true}
              onClose={() => setIsConnectModalOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
