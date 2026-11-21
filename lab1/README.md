# Лабораторна робота №1. Архітектурний рефакторинг та принципи SOLID

Дисципліна: «Програмна інженерія (Software Engineering)»
Виконав: Бруско Максим, група МФ-51

Мова: Python 3.10+. Запуск: `python main.py`. Перевірка: `python test_order_service.py`.

## Структура

```
lab1/
├── original/order_processor.py   # вихідний код («God Object»), номери рядків нижче — звідси
├── shop/
│   ├── models.py                 # Order, Item
│   ├── validation.py             # OrderValidator + NonEmptyOrderValidator
│   ├── order_service.py          # OrderService — залежить лише від абстракцій
│   ├── discounts/                # DiscountStrategy + VipDiscount, StandardDiscount
│   ├── payments/                 # PaymentProcessor + CreditCard, Crypto
│   ├── repositories/             # OrderRepository + MySqlOrderRepository
│   ├── notifiers/                # Notifier + EmailNotifier
│   └── extensions/               # Завдання 3: WholesaleDiscount, PayPal, SmsNotifier
├── main.py                       # composition root: тут обираються конкретні класи
└── test_order_service.py
```

## Завдання 1. Аналіз та Code Review

| Принцип | Де порушено | У чому проблема |
|---|---|---|
| **S** — Single Responsibility | увесь метод `process_order`, рядки 2–28 | Один клас валідує (4–5), рахує знижку (8–14), списує оплату (17–22), зберігає в БД (25) і надсилає лист (28). У нього п'ять причин змінюватися: зміна будь-якої з цих частин зачіпає один і той самий метод, а протестувати знижку окремо від оплати й бази неможливо. |
| **O** — Open/Closed | рядки 9–12 (типи клієнтів), 17–22 (способи оплати) | Ланцюжки `if/elif` за рядковими значеннями. Щоб додати тип клієнта чи PayPal, треба правити вже робочий код і перетестовувати весь метод. |
| **D** — Dependency Inversion | рядки 17–22 (Stripe, Coinbase), 25 (MySQL), 28 (Email) | Бізнес-логіка напряму прив'язана до конкретних сервісів. Не можна підмінити MySQL на іншу БД чи Email на SMS, не переписавши клас; у тестах неможливо підставити заглушки. |
| **I** — Interface Segregation | клас загалом | Окремих інтерфейсів немає: увесь клас — один «товстий» контракт. Клієнт, якому потрібен лише розрахунок знижки, залежить і від оплати, і від БД, і від пошти. |
| **L** — Liskov Substitution | — | Ієрархії класів немає, тож прямого порушення LSP немає. Але й підставити іншу реалізацію (наприклад, іншу оплату) нікуди — це наслідок порушення D, а не L. |

Додаткові проблеми, які виявив рев'ю:

- **Мовчазна помилка оплати (рядки 17–22).** Невідомий `payment_type` (наприклад, `"Cash"`) не обробляється: оплата не проходить, але замовлення все одно зберігається (25) і клієнт отримує лист «Your order is processed» (28).
- **Невідомий тип клієнта (рядок 8)** мовчки отримує знижку 0 замість помилки.
- **`raise Exception` (рядок 5)** — загальний виняток, який не можна перехопити окремо від інших помилок.

## Завдання 2. Рефакторинг

- **Знижки — патерн Strategy.** `DiscountStrategy` з методом `rate()`; реалізації `VipDiscount` (20%) і `StandardDiscount` (5%).
- **Абстракції** `PaymentProcessor`, `OrderRepository`, `Notifier`, а також `OrderValidator` (валідація теж окрема відповідальність).
- **Dependency Injection.** `OrderService` отримує всі залежності через конструктор: валідатор, словники `тип клієнта → стратегія` і `спосіб оплати → процесор`, репозиторій і нотифікатор.
- **`OrderService` імпортує лише модулі `base`** (абстракції). Конкретні класи створюються тільки в `main.py`. Це перевіряє тест `test_order_service_depends_only_on_abstractions`.
- Невідомий тип клієнта чи оплати дає `UnsupportedOptionError` **до** списання і збереження — баг з рев'ю закрито.

## Завдання 3. Розширення без зміни наявних класів

Додано лише нові файли в `shop/extensions/`:

| Що | Клас | Як підключається |
|---|---|---|
| Тип клієнта «Wholesale», знижка 30% | `WholesaleDiscount(DiscountStrategy)` | новий ключ `"Wholesale"` у словнику знижок |
| Оплата PayPal | `PayPalPaymentProcessor(PaymentProcessor)` | новий ключ `"PayPal"` у словнику оплат |
| SMS замість Email | `SmsNotifier(Notifier)` | передається в конструктор замість `EmailNotifier` |

Підключення показано в `main.py`, функція `build_extended_service()`. Жоден файл із Завдання 2 не змінювався: змінилася лише конфігурація в composition root, а це місце якраз і призначене для вибору конкретних реалізацій.

Результат `python main.py`:

```
=== Базова конфігурація ===
Processing credit card payment for 840.0
Saving order 1 (total 840.0) to MySQL Database...
Sending Email to vip@example.com: Your order is processed.

=== Розширена конфігурація (Завдання 3) ===
Processing PayPal payment for 735.0
Saving order 2 (total 735.0) to MySQL Database...
Sending SMS to +380501234567: Your order is processed.
```

## Завдання 4. UML-діаграма класів

```mermaid
classDiagram
    direction LR

    class OrderService {
        -validator: OrderValidator
        -discounts: dict of DiscountStrategy
        -payments: dict of PaymentProcessor
        -repository: OrderRepository
        -notifier: Notifier
        +process_order(order, payment_type) float
    }

    class OrderValidator {
        <<interface>>
        +validate(order)
    }
    class DiscountStrategy {
        <<interface>>
        +rate() float
        +apply(amount) float
    }
    class PaymentProcessor {
        <<interface>>
        +pay(amount)
    }
    class OrderRepository {
        <<interface>>
        +save(order, total)
    }
    class Notifier {
        <<interface>>
        +notify(order, message)
    }

    OrderService ..> OrderValidator
    OrderService ..> DiscountStrategy
    OrderService ..> PaymentProcessor
    OrderService ..> OrderRepository
    OrderService ..> Notifier

    OrderValidator <|.. NonEmptyOrderValidator
    DiscountStrategy <|.. VipDiscount
    DiscountStrategy <|.. StandardDiscount
    DiscountStrategy <|.. WholesaleDiscount
    PaymentProcessor <|.. CreditCardPaymentProcessor
    PaymentProcessor <|.. CryptoPaymentProcessor
    PaymentProcessor <|.. PayPalPaymentProcessor
    OrderRepository <|.. MySqlOrderRepository
    Notifier <|.. EmailNotifier
    Notifier <|.. SmsNotifier
```

`..>` — залежність (Dependency): `OrderService` використовує лише інтерфейси. `<|..` — реалізація (Realization). `WholesaleDiscount`, `PayPalPaymentProcessor` і `SmsNotifier` — класи із Завдання 3.

## Декларування використання ШІ

[ ] Під час виконання цієї лабораторної роботи інструменти генеративного ШІ НЕ використовувалися.

[X] Під час виконання цієї лабораторної роботи використовувалися інструменти ШІ як допоміжний засіб.

| Інструмент ШІ | Список промптів або опис задачі, делегованої ШІ |
|---|---|
| Claude (Anthropic) | 1. Надіслано умову лабораторної роботи №1 (SOLID). 2. «Зроби все, що можна, з того, що в роботі» — ШІ підготував рефакторинг, тести, README і UML-діаграму. 3. *(допиши свої подальші промпти, якщо будуть)* |
