import { Routes, Route } from 'react-router-dom';
import BottomNav from './components/BottomNav';
import NearbyHospitals from './components/NearbyHospitals';
import PrivateRoute from './components/PrivateRoute';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Assessment from './pages/Assessment';
import Upload from './pages/Upload';
import History from './pages/History';
import Alerts from './pages/Alerts';
import Profile from './pages/Profile';
import Caretaker from './pages/Caretaker';
import Assistant from './pages/Assistant';

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/assessment" element={<PrivateRoute><Assessment /></PrivateRoute>} />
        <Route path="/upload" element={<PrivateRoute><Upload /></PrivateRoute>} />
        <Route path="/history" element={<PrivateRoute><History /></PrivateRoute>} />
        <Route path="/alerts" element={<PrivateRoute><Alerts /></PrivateRoute>} />
        <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
        <Route path="/caretaker" element={<PrivateRoute><Caretaker /></PrivateRoute>} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="*" element={<Landing />} />
      </Routes>
      <NearbyHospitals />
      <BottomNav />
    </>
  );
}