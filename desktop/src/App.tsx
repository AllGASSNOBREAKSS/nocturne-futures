import { Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import Overview from "./pages/Overview";
import Predict from "./pages/Predict";
import BacktestCenter from "./pages/BacktestCenter";
import Market from "./pages/Market";
import Predictions from "./pages/Predictions";
import ModelStudio from "./pages/ModelStudio";
import StrategyLab from "./pages/StrategyLab";
import Backtests from "./pages/Backtests";
import Signals from "./pages/Signals";
import Performance from "./pages/Performance";
import Intelligence from "./pages/Intelligence";
import Operations from "./pages/Operations";

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Predict />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/market" element={<Market />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/models" element={<ModelStudio />} />
        <Route path="/test" element={<BacktestCenter />} />
        <Route path="/lab" element={<StrategyLab />} />
        <Route path="/backtests" element={<Backtests />} />
        <Route path="/backtests/:id" element={<Backtests />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/performance" element={<Performance />} />
        <Route path="/intel" element={<Intelligence />} />
        <Route path="/ops" element={<Operations />} />
      </Routes>
    </Shell>
  );
}
