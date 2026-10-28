# HatHouse на Django

## Локальний запуск

У PowerShell з каталогу проєкту:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Вітрина: http://127.0.0.1:8000/  
Адмін-панель: http://127.0.0.1:8000/admin/

Відвідувачі можуть створити акаунт через посилання «Реєстрація». Нові акаунти не мають адміністративних прав. Створюй суперкористувача локально командою `python manage.py createsuperuser`; не зберігай пароль у репозиторії.

Початкові категорії, п’ять товарів і сторінки контактів, повернень та угоди додаються міграціями. Фото, завантажені через адмін-панель, зберігаються в `media/`.

## Deploy на Render

1. Push код до GitHub і переконайся, що в репозиторії немає `.env`, паролів або ключів.
2. Створи Render PostgreSQL у потрібному регіоні та скопіюй **Internal Database URL**.
3. У Render вибери **New Blueprint**, підключи репозиторій і застосуй кореневий `render.yaml`. На запит `DATABASE_URL` встав Internal Database URL. `DJANGO_SECRET_KEY` буде згенеровано автоматично.
4. Після першого deploy створюй адміністратора в Shell сервісу: `python manage.py createsuperuser`.
5. Для власного домену задай `DJANGO_ALLOWED_HOSTS` (лише hostname, без `https://`) і `DJANGO_CSRF_TRUSTED_ORIGINS` (повний origin, наприклад `https://shop.example.com`). Render hostname додається автоматично.
6. Для платежів додай у Environment Variables `LIQPAY_PUBLIC_KEY`, `LIQPAY_PRIVATE_KEY` і `LIQPAY_SANDBOX`; секретний ключ не додавай до GitHub.

Blueprint запускає `bash build.sh`, який встановлює залежності, збирає статику й застосовує міграції. Сайт стартує через Gunicorn.

**Завантажені фото:** Render filesystem за замовчуванням непостійний, а `/media/` у цьому проєкті зараз обслуговується лише в DEBUG. Перед використанням завантажених через адмінку фото в production налаштуй S3-сумісне сховище (наприклад, Cloudinary або S3) або окрему production media-конфігурацію. Не покладайся на локальні файли вебсервісу після redeploy.

## Оплата замовлень

Checkout перевіряє склад кошика та ціни на сервері, зберігає замовлення і передає покупця на захищену сторінку LiqPay. Реквізити картки сайт не отримує. Для тестового режиму задайте ключі мерчанта LiqPay у PowerShell перед запуском сервера:

```powershell
$env:LIQPAY_PUBLIC_KEY = "ваш_публічний_ключ"
$env:LIQPAY_PRIVATE_KEY = "ваш_приватний_ключ"
$env:LIQPAY_SANDBOX = "1"
python manage.py runserver
```

Без ключів форма checkout буде доступна для перегляду, але кнопка оплати залишиться вимкненою. Для реальних платежів задайте бойові ключі та `LIQPAY_SANDBOX=0`; ніколи не додавайте приватний ключ до репозиторію. Callback LiqPay використовує `/payments/liqpay/callback/`, тому для приймання підтверджень потрібен публічно доступний HTTPS-домен.

## Перед публікацією

Задайте `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` та `DJANGO_ALLOWED_HOSTS` для домену. Налаштуйте HTTPS і постійне сховище для бази даних та `media/`; зберіть статику командою `python manage.py collectstatic`. `runserver` призначений лише для локальної розробки.
