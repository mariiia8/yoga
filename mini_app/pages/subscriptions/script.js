const TEST_MODE = false;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
            Telegram.WebApp.expand();
            const userId = Telegram.WebApp.initDataUnsafe?.user?.id || 470064868;
            await loadSubscriptions(userId);
            Telegram.WebApp.ready();
        } else {
            console.warn('Telegram WebApp API not available - running in browser mode');
            await loadSubscriptions(470064868);
        }
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    }
});

// Тестовые данные для демонстрации
const TEST_SUBSCRIPTIONS = [
    {
        id: 1,
        name: "Абонемент на 5 занятий",
        class_name: "Йога для начинающих",
        visits_allowed: 5,
        visits_remaining: 3,
        price: 3500,
        purchase_date: "2023-05-15"
    },
    {
        id: 2,
        name: "Абонемент на 10 занятий",
        class_name: "Продвинутая йога",
        visits_allowed: 10,
        visits_remaining: 7,
        price: 6000,
        purchase_date: "2023-06-01"
    }
];

async function loadSubscriptions(userId) {
    let subscriptions;
    
    if (TEST_MODE) {
        // Используем тестовые данные в режиме разработки
        subscriptions = TEST_SUBSCRIPTIONS;
    } else {
        try {
            const response = await fetch(`/api/user/active_subscriptions?user_id=${userId}`);
            if (!response.ok) {
                throw new Error('Failed to load subscriptions');
            }
            subscriptions = await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            showError('Ошибка загрузки данных. Пожалуйста, попробуйте позже.');
            return;
        }
    }
    
    const container = document.querySelector('.subscriptions-container');
    if (!container) return;
    
    container.innerHTML = `
        <a href="/" class="back-button">← На главную</a>
        <h1 class="subscriptions-title">💳 Мои абонементы</h1>
        <div class="subscriptions-grid" id="subscriptions-list"></div>
    `;
    
    const list = document.getElementById('subscriptions-list');
    if (!list) return;
    
    if (!subscriptions || subscriptions.length === 0) {
        list.innerHTML = `
            <div class="no-subscriptions">
                <p>У вас нет активных абонементов</p>
                <a href="/schedule" class="action-button">Посмотреть расписание</a>
            </div>
        `;
        return;
    }
    
    subscriptions.forEach(sub => {
        const card = document.createElement('div');
        card.className = 'subscription-card';
        card.innerHTML = `
            <div class="subscription-header">
                <h3 class="subscription-name">${sub.name}</h3>
                <span class="subscription-price">${sub.price} ₽</span>
            </div>
            <p class="subscription-class">Для: ${sub.class_name}</p>
            <div class="subscription-details">
                <p>Куплен: ${new Date(sub.purchase_date).toLocaleDateString()}</p>
                <p>Занятий всего: ${sub.visits_allowed}</p>
                <span class="visits-remaining">Осталось: ${sub.visits_remaining}</span>
            </div>
        `;
        list.appendChild(card);
    });
}

function showError(message) {
    const container = document.querySelector('.subscriptions-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="error-container">
            <p>${message}</p>
            <button onclick="location.reload()" class="action-button">Попробовать снова</button>
        </div>
    `;
}
