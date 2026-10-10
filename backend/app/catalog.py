"""Справочники платформы (CONTRACT 8.1). Генератор данных и бэкенд берут их отсюда."""

SPECS: dict[str, str] = {
    "backend": "Бэкенд-разработчик",
    "frontend": "Фронтенд-разработчик",
    "bas": "БАС-разработчик",
}

GRADES: list[str] = ["junior", "middle", "senior"]
GRADE_TITLES: dict[str, str] = {"junior": "Junior", "middle": "Middle", "senior": "Senior"}

# Порог θ (шкала Раша), с которого грейд считается подтверждённым (CONTRACT 2).
THRESHOLDS: dict[str, float] = {"junior": -0.5, "middle": 0.5, "senior": 1.5}

SKILLS: dict[str, list[str]] = {
    "backend": ["Python", "Go", "Java", "FastAPI", "Django", "Spring", "PostgreSQL", "Redis", "Kafka",
                "Docker", "Kubernetes", "Linux", "REST", "gRPC", "SQL"],
    "frontend": ["JavaScript", "TypeScript", "React", "Vue", "Next.js", "Redux", "HTML", "CSS", "Vite",
                 "Webpack", "Jest", "REST", "Figma", "Accessibility"],
    "bas": ["Python", "C++", "Embedded C", "Linux", "MAVLink", "ArduPilot", "PX4", "ROS 2", "GNSS",
            "Kalman filter", "Computer Vision", "Docker", "SQL"],
}

ALL_SKILLS: list[str] = sorted({s for skills in SKILLS.values() for s in skills})

FSP_DISCIPLINES: list[str] = [
    "продуктовое программирование",
    "алгоритмическое программирование",
    "программирование систем информационной безопасности",
    "программирование робототехники",
    "программирование беспилотных авиационных систем",
]

# Дисциплины, близкие специализации, получают множитель 1,5; остальные равноценны (1,0).
RELEVANT_DISCIPLINES: dict[str, set[str]] = {
    "backend": {"продуктовое программирование"},
    "frontend": {"продуктовое программирование"},
    "bas": {"программирование беспилотных авиационных систем", "программирование робототехники"},
}
RELEVANCE_MULTIPLIER = 1.5

RESULT_ROLES: list[str] = ["winner", "prize", "participant"]
ROLE_TITLES: dict[str, str] = {"winner": "Победитель", "prize": "Призёр", "participant": "Участник"}

WORK_FORMATS: list[str] = ["office", "remote", "hybrid"]
WORK_FORMAT_TITLES: dict[str, str] = {"office": "офис", "remote": "удалённо", "hybrid": "гибрид"}

SALARY_TYPES: list[str] = ["gross", "net"]
