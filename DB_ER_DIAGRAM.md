# db.sqlite3 實際資料庫結構與 ER 圖

> 來源：直接讀取目前 `db.sqlite3` 的 SQLite metadata（table info、foreign keys、unique indexes）。

## 資料表總覽

目前共有 **21 張資料表**：

- 核心業務表（9）：`myapp_custommember`、`myapp_dish`、`myapp_menuitem`、`myapp_reservation`、`myapp_cartitem`、`myapp_order`、`myapp_orderitem`、`myapp_financialcategory`、`myapp_financialrecord`
- 會員權限中介表（2）：`myapp_custommember_groups`、`myapp_custommember_user_permissions`
- Django／登入套件系統表（10）：`account_emailaddress`、`account_emailconfirmation`、`auth_group`、`auth_group_permissions`、`auth_permission`、`django_admin_log`、`django_content_type`、`django_migrations`、`django_session`、`django_site`

## 核心業務 ER 圖

```mermaid
erDiagram
    MYAPP_CUSTOMMEMBER {
        INTEGER id PK
        DATETIME last_login "nullable"
        BOOLEAN is_superuser
        VARCHAR username UK
        VARCHAR last_name
        VARCHAR first_name
        VARCHAR password
        VARCHAR email UK
        VARCHAR phone "nullable"
        DATE birthday "nullable"
        VARCHAR gender "nullable"
        DATETIME created_at
        BOOLEAN is_active
        BOOLEAN is_staff
    }

    MYAPP_DISH {
        INTEGER id PK
        VARCHAR name
        INTEGER price
        VARCHAR image
        INTEGER spicy_level
        TEXT description "nullable"
        BOOLEAN is_recommended
        BOOLEAN is_available
        VARCHAR category
    }

    MYAPP_MENUITEM {
        INTEGER id PK
        VARCHAR name
        INTEGER price
        BOOLEAN is_available
    }

    MYAPP_RESERVATION {
        INTEGER id PK
        VARCHAR name
        VARCHAR phone
        VARCHAR email "nullable"
        DATE date
        VARCHAR time_slot
        INTEGER guests
        TEXT notes "nullable"
        DATETIME created_at
        INTEGER user_id FK
        BOOLEAN is_arrived
    }

    MYAPP_CARTITEM {
        INTEGER id PK
        INTEGER quantity
        DATETIME created_at
        INTEGER member_id FK
        INTEGER item_id FK
    }

    MYAPP_ORDER {
        INTEGER id PK
        INTEGER total_amount
        VARCHAR status
        VARCHAR merchant_trade_no UK "nullable"
        DATETIME pickup_time
        DATETIME created_at
        INTEGER member_id FK
    }

    MYAPP_ORDERITEM {
        INTEGER id PK
        VARCHAR item_name
        INTEGER price
        INTEGER quantity
        INTEGER order_id FK
    }

    MYAPP_FINANCIALCATEGORY {
        INTEGER id PK
        VARCHAR record_type
        VARCHAR name
    }

    MYAPP_FINANCIALRECORD {
        INTEGER id PK
        DECIMAL amount
        DATE date
        TEXT note "nullable"
        INTEGER category_id FK
        INTEGER order_id FK,UK "nullable"
    }

    MYAPP_CUSTOMMEMBER ||--o{ MYAPP_RESERVATION : "user_id"
    MYAPP_CUSTOMMEMBER ||--o{ MYAPP_CARTITEM : "member_id"
    MYAPP_DISH ||--o{ MYAPP_CARTITEM : "item_id"
    MYAPP_CUSTOMMEMBER ||--o{ MYAPP_ORDER : "member_id"
    MYAPP_ORDER ||--o{ MYAPP_ORDERITEM : "order_id"
    MYAPP_FINANCIALCATEGORY ||--o{ MYAPP_FINANCIALRECORD : "category_id"
    MYAPP_ORDER o|--o| MYAPP_FINANCIALRECORD : "order_id (unique, nullable)"
```

## 帳號、權限與 Django 系統 ER 圖

```mermaid
erDiagram
    MYAPP_CUSTOMMEMBER {
        INTEGER id PK
        VARCHAR username UK
        VARCHAR email UK
    }

    ACCOUNT_EMAILADDRESS {
        INTEGER id PK
        BOOLEAN verified
        BOOLEAN primary
        INTEGER user_id FK
        VARCHAR email UK
    }

    ACCOUNT_EMAILCONFIRMATION {
        INTEGER id PK
        DATETIME created
        DATETIME sent "nullable"
        VARCHAR key UK
        INTEGER email_address_id FK
    }

    AUTH_GROUP {
        INTEGER id PK
        VARCHAR name UK
    }

    AUTH_PERMISSION {
        INTEGER id PK
        INTEGER content_type_id FK
        VARCHAR codename
        VARCHAR name
    }

    AUTH_GROUP_PERMISSIONS {
        INTEGER id PK
        INTEGER group_id FK
        INTEGER permission_id FK
    }

    MYAPP_CUSTOMMEMBER_GROUPS {
        INTEGER id PK
        INTEGER custommember_id FK
        INTEGER group_id FK
    }

    MYAPP_CUSTOMMEMBER_USER_PERMISSIONS {
        INTEGER id PK
        INTEGER custommember_id FK
        INTEGER permission_id FK
    }

    DJANGO_CONTENT_TYPE {
        INTEGER id PK
        VARCHAR app_label
        VARCHAR model
    }

    DJANGO_ADMIN_LOG {
        INTEGER id PK
        TEXT object_id "nullable"
        VARCHAR object_repr
        SMALLINT action_flag
        TEXT change_message
        INTEGER content_type_id FK "nullable"
        INTEGER user_id FK
        DATETIME action_time
    }

    DJANGO_MIGRATIONS {
        INTEGER id PK
        VARCHAR app
        VARCHAR name
        DATETIME applied
    }

    DJANGO_SESSION {
        VARCHAR session_key PK
        TEXT session_data
        DATETIME expire_date
    }

    DJANGO_SITE {
        INTEGER id PK
        VARCHAR name
        VARCHAR domain UK
    }

    MYAPP_CUSTOMMEMBER ||--o{ ACCOUNT_EMAILADDRESS : "user_id"
    ACCOUNT_EMAILADDRESS ||--o{ ACCOUNT_EMAILCONFIRMATION : "email_address_id"

    MYAPP_CUSTOMMEMBER ||--o{ MYAPP_CUSTOMMEMBER_GROUPS : "custommember_id"
    AUTH_GROUP ||--o{ MYAPP_CUSTOMMEMBER_GROUPS : "group_id"

    MYAPP_CUSTOMMEMBER ||--o{ MYAPP_CUSTOMMEMBER_USER_PERMISSIONS : "custommember_id"
    AUTH_PERMISSION ||--o{ MYAPP_CUSTOMMEMBER_USER_PERMISSIONS : "permission_id"

    AUTH_GROUP ||--o{ AUTH_GROUP_PERMISSIONS : "group_id"
    AUTH_PERMISSION ||--o{ AUTH_GROUP_PERMISSIONS : "permission_id"

    DJANGO_CONTENT_TYPE ||--o{ AUTH_PERMISSION : "content_type_id"
    DJANGO_CONTENT_TYPE o|--o{ DJANGO_ADMIN_LOG : "content_type_id"
    MYAPP_CUSTOMMEMBER ||--o{ DJANGO_ADMIN_LOG : "user_id"
```

## 關聯重點

- 一位會員可有多筆訂位、購物車項目及訂單。
- 一道菜可出現在多筆購物車項目中。
- 一張訂單可有多筆訂單明細；訂單明細儲存餐點名稱與價格快照，**沒有直接外鍵連到 `myapp_dish`**。
- 一個財務科目可有多筆財務紀錄。
- `myapp_financialrecord.order_id` 可為空且有唯一約束，因此訂單與財務紀錄為「雙方皆可不存在的一對一」。
- `myapp_menuitem`、`django_migrations`、`django_session`、`django_site` 沒有外鍵關聯。
- SQLite metadata 中的外鍵刪除動作均為 `NO ACTION`；`CASCADE`、`PROTECT`、`SET_NULL` 等行為主要由 Django ORM 的 model 設定處理。

