import { Navigate, Route, Routes } from "react-router-dom";
import Guard from "./components/Guard";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Category from "./pages/candidate/Category";
import CandidateInvitations from "./pages/candidate/Invitations";
import Journey from "./pages/candidate/Journey";
import Profile from "./pages/candidate/Profile";
import TestResult from "./pages/candidate/TestResult";
import TestRun from "./pages/candidate/TestRun";
import Vacancies from "./pages/candidate/Vacancies";
import CandidateTasks from "./pages/candidate/Tasks";
import EmployerTasks from "./pages/employer/Tasks";
import CandidatePage from "./pages/employer/CandidatePage";
import Company from "./pages/employer/Company";
import EmployerInvitations from "./pages/employer/Invitations";
import NeedMatches from "./pages/employer/NeedMatches";
import Needs from "./pages/employer/Needs";
import Search from "./pages/employer/Search";

// Маршруты обоих кабинетов.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />

        <Route path="candidate" element={<Guard role="candidate" />}>
          <Route index element={<Journey />} />
          <Route path="profile" element={<Profile />} />
          <Route path="test/:attemptId" element={<TestRun />} />
          <Route path="result/:attemptId" element={<TestResult />} />
          <Route path="category" element={<Category />} />
          <Route path="invitations" element={<CandidateInvitations />} />
          <Route path="vacancies" element={<Vacancies />} />
          <Route path="tasks" element={<CandidateTasks />} />
        </Route>

        <Route path="employer" element={<Guard role="employer" />}>
          <Route index element={<Needs />} />
          <Route path="needs/:needId" element={<NeedMatches />} />
          <Route path="search" element={<Search />} />
          <Route path="candidates/:candId" element={<CandidatePage />} />
          <Route path="invitations" element={<EmployerInvitations />} />
          <Route path="company" element={<Company />} />
          <Route path="tasks" element={<EmployerTasks />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
