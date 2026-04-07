import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import NewValuation from "@/pages/NewValuation";
import Results from "@/pages/Results";
import History from "@/pages/History";
import SharedView from "@/pages/SharedView";
import Settings from "@/pages/Settings";
import Simulator from "@/pages/Simulator";

function App() {
  return (
    <div className="App min-h-screen bg-white">
      <Toaster position="top-right" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/new" element={<NewValuation />} />
          <Route path="/results/:id" element={<Results />} />
          <Route path="/simulator/:id" element={<Simulator />} />
          <Route path="/history" element={<History />} />
          <Route path="/share/:shareId" element={<SharedView />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
