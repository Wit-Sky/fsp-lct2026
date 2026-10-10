import { Navigate, Route, Routes } from "react-router-dom";
import Guard from "./components/Guard";
import Layout from "./components/Layout";
import Placeholder from "./components/Placeholder";
import Home from "./pages/Home";

// Маршруты обоих кабинетов. Экраны-заглушки заменяются настоящими на шаге 2 (team/EVGENY.md).
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />

        <Route path="candidate" element={<Guard role="candidate" />}>
          <Route index element={<Placeholder title="Мой путь" hint="Профиль → ФСП ID → специализация и грейд → тест → категория." />} />
          <Route path="profile" element={<Placeholder title="Профиль и резюме" />} />
          <Route path="test/:attemptId" element={<Placeholder title="Тест" />} />
          <Route path="result/:attemptId" element={<Placeholder title="Результат теста" />} />
          <Route path="category" element={<Placeholder title="Моя категория" />} />
          <Route path="invitations" element={<Placeholder title="Приглашения" />} />
          <Route path="vacancies" element={<Placeholder title="Вакансии" />} />
        </Route>

        <Route path="employer" element={<Guard role="employer" />}>
          <Route index element={<Placeholder title="Подбор" hint="Мастер «Кого вы ищете» и список потребностей." />} />
          <Route path="needs/:needId" element={<Placeholder title="Подборка кандидатов" />} />
          <Route path="search" element={<Placeholder title="База кандидатов" />} />
          <Route path="candidates/:candId" element={<Placeholder title="Карточка кандидата" />} />
          <Route path="invitations" element={<Placeholder title="Мои приглашения" />} />
          <Route path="company" element={<Placeholder title="Профиль компании" />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
