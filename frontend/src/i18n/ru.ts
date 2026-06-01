export const RU = {
  common: {
    loading: "Загрузка…",
    unknown_error: "Неизвестная ошибка",
    not_available: "Недоступно",
  },
  auth: {
    sign_in_title: "Вход",
    sign_in_subtitle:
      "Войдите в аккаунт продавца, чтобы открыть дашборды, загрузки и ежедневные подсказки.",
    email: "Email",
    password: "Пароль",
    sign_in: "Войти",
    signing_in: "Входим…",
    signed_in: "Вход выполнен",
    welcome_back: "С возвращением",
    login_failed: "Не удалось войти",
    new_here: "Впервые здесь?",
    create_account: "Создать аккаунт",

    register_title: "Создать аккаунт",
    register_subtitle:
      "Аккаунт изолирован на уровне данных (RLS): вы видите только свои загрузки и производные метрики.",
    password_hint: "Минимум 8 символов.",
    creating: "Создаём…",
    create: "Создать",
    account_created: "Аккаунт создан",
    you_can_sign_in_now: "Теперь можно войти.",
    registration_failed: "Не удалось зарегистрироваться",
    already_have_account: "Уже есть аккаунт?",
  },
  ai: {
    inbox_title: "Входящие рекомендации",
    inbox_subtitle:
      "Приоритизированные действия с оценкой эффекта, срочностью и доказательствами. AI — только советник.",
    todays_focus: "Что важно сегодня →",
    daily_digest: "Дайджест дня →",
    stats_open: "Активные",
    stats_conversion: "Конверсия в действия",
    stats_completed: "Выполнено",
    stats_ignored_7d: "Игнор 7д",
    inbox_empty_title: "Входящие пусты",
    inbox_empty_hint: "Загрузите отчёты, запустите анализ или откройте вкладки «Сохранено/Отложено».",
    band_today: "Сегодня",
    band_this_week: "На этой неделе",
    band_informational: "К сведению",

    action_save: "Сохранить",
    action_snooze_7d: "Отложить на 7 дней",
    action_dismiss: "Скрыть",

    stream_error_prefix: "[ошибка]",
    rec_fallback_title: "Рекомендация",
  },
  trust: {
    trust_transparency: "Достоверность и прозрачность",
    advisory_only: "Только рекомендация",
    urgency: "Срочность",
  },
} as const;

