document.addEventListener('DOMContentLoaded', () => {
    // Инициализация Telegram WebApp
    initTelegramWebApp();
    
    // Загрузка данных пользователя
    loadUserData();
});

function initTelegramWebApp() {
    if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
        Telegram.WebApp.expand();
        Telegram.WebApp.ready();
    }
}

function loadUserData() {
    // Получаем данные пользователя из Telegram WebApp
    const tgUser = Telegram.WebApp.initDataUnsafe?.user;
    
    if (tgUser) {
        updateUserGreeting(tgUser);
        
        // Дополнительно можно запросить данные с сервера
        // fetchUserDataFromServer(tgUser.id);
    }
}

function updateUserGreeting(tgUser) {
    const usernameElement = document.getElementById('username');
    
    if (tgUser.first_name || tgUser.last_name) {
        const firstName = tgUser.first_name || '';
        const lastName = tgUser.last_name || '';
        usernameElement.textContent = `${firstName}, Добро пожаловать!`;
    } else if (tgUser.username) {
        usernameElement.textContent = `Добро пожаловать, @${tgUser.username}!`;
    }
}

async function fetchUserDataFromServer(userId) {
    try {
        const response = await fetch(`/api/user?user_id=${userId}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch user data');
        }
        
        const userData = await response.json();
        
        if (userData.name) {
            document.getElementById('username').textContent = `Добро пожаловать, ${userData.name}!`;
        }
    } catch (error) {
        console.error('Error fetching user data:', error);
    }
}
