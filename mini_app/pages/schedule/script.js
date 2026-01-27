const TEST_MODE = false;

const TEST_CLASSES = [
    {
        id: 1,
        name: "Йога для начинающих",
        description: "Базовые асаны для новичков. Подходит для любого уровня подготовки.",
        datetime: new Date(Date.now() + 86400000).toISOString(),
        price: 800,
        max_participants: 10
    },
    {
        id: 2,
        name: "Продвинутая йога",
        description: "Сложные асаны и последовательности для опытных практиков.",
        datetime: new Date(Date.now() + 172800000).toISOString(),
        price: 1000,
        max_participants: 8
    },
    {
        id: 3,
        name: "Йога для беременных",
        description: "Специальные упражнения для будущих мам.",
        datetime: new Date(Date.now() + 259200000).toISOString(),
        price: 900,
        max_participants: 6
    }
];

const TEST_SUBSCRIPTIONS = [
    {
        id: 1,
        name: "Абонемент на 5 занятий",
        visits_allowed: 5,
        price: 3500,
        class_id: 1
    },
    {
        id: 2,
        name: "Абонемент на 10 занятий",
        visits_allowed: 10,
        price: 6000,
        class_id: 1
    }
];

const TEST_BOOKINGS = [
    {
        id: 1,
        class_id: 1,
        user_id: 470064868,
        datetime: new Date().toISOString()
    }
];

document.addEventListener('DOMContentLoaded', async () => {
    if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
        try {
            Telegram.WebApp.expand();
            const userId = Telegram.WebApp.initDataUnsafe?.user?.id || 470064868; // Тестовый ID
            
            await loadClasses(userId);
            Telegram.WebApp.ready();
        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
        }
    } else {
        console.warn('Telegram WebApp API not available - running in browser mode');
        await loadClasses(470064868); // Тестовый режим
    }
});

async function loadClasses(userId) {
    let classes, subscriptions, bookings;
    
    if (TEST_MODE) {
        classes = TEST_CLASSES;
        subscriptions = TEST_SUBSCRIPTIONS; 
        bookings = TEST_BOOKINGS; 
    } else {
        const [classesResponse, subscriptionsResponse, bookingsResponse] = await Promise.all([
            fetch(`/api/classes?user_id=${userId}`),
            fetch(`/api/user/active_subscriptions?user_id=${userId}`),
            fetch(`/api/user/bookings?user_id=${userId}`)
        ]);
        
        classes = await classesResponse.json();
        subscriptions = await subscriptionsResponse.json();
        bookings = await bookingsResponse.json();
    }
    
    const container = document.querySelector('.schedule-container');
    container.innerHTML = `
        <a href="/" class="back-button">← На главную</a>
        <h1 class="classes-title">📅 Расписание занятий</h1>
        <div class="classes-grid" id="classes-list"></div>
    `;
    
    const list = document.getElementById('classes-list');
    
    classes.forEach(cls => {
        const classDate = new Date(cls.datetime);
        const isPast = classDate < new Date();
        const hasSubscription = subscriptions.some(s => s.class_id === cls.id && s.visits_remaining > 0);
        const isBooked = bookings.some(b => b.class_id === cls.id);
        
        const card = document.createElement('div');
        card.className = 'class-card';
        card.innerHTML = `
            <h3 class="class-title">${cls.name}</h3>
            ${isPast ? '<div class="past-badge">Прошло</div>' : ''}
            ${isBooked ? '<div class="booking-badge">Вы записаны</div>' : ''}
            <div class="class-meta">
                <span>📅 ${classDate.toLocaleString()}</span>
                <span>${cls.price} ₽</span>
            </div>
            <p class="class-description">${cls.description}</p>
            <div class="class-actions">
                ${isPast
                    ? '<button class="action-button" disabled>Запись закрыта</button>'
                    : hasSubscription 
                        ? isBooked 
                            ? `<button class="action-button cancel-button" 
                                 onclick="cancelBooking(${bookings.find(b => b.class_id === cls.id).id}, ${cls.id}, ${userId})">
                                 Не приду
                               </button>`
                            : `<button class="action-button book-button" 
                                 onclick="handleBooking(${cls.id}, ${userId})">
                                 Записаться
                               </button>`
                        : `<button class="action-button subscribe-button" 
                             onclick="showSubscriptionOptions(${cls.id}, ${userId})">
                             Купить абонемент
                           </button>`}
            </div>
        `;
        list.appendChild(card);
    });
}

function showSubscriptionOptions(classId, userId) {
    const modal = document.createElement('div');
    modal.className = 'subscription-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Выберите абонемент</h3>
            <div id="subscription-options"></div>
            <button class="close-modal" onclick="this.parentElement.parentElement.remove()">Закрыть</button>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    fetch(`/api/class/${classId}/subscription_types`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch subscription options');
            }
            return response.json();
        })
        .then(options => {
            const container = document.getElementById('subscription-options');
            if (!options || !Array.isArray(options)) {
                container.innerHTML = '<p>Нет доступных абонементов для этого занятия</p>';
                return;
            }
            
            options.forEach(option => {
                const optionEl = document.createElement('div');
                optionEl.className = 'subscription-option';
                optionEl.innerHTML = `
                    <h4>${option.name}</h4>
                    <p>${option.visits_allowed} занятий</p>
                    <p>${option.price} ₽</p>
                    <button onclick="purchaseSubscription(${option.id}, ${userId}, ${classId})">Купить</button>
                `;
                container.appendChild(optionEl);
            });
        })
        .catch(error => {
            console.error('Error loading subscription options:', error);
            const container = document.getElementById('subscription-options');
            container.innerHTML = `<p>Ошибка загрузки абонементов: ${error.message}</p>`;
        });
}

async function purchaseSubscription(subscriptionTypeId, userId, classId) {
    try {
        const response = await fetch('/api/subscriptions/purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: userId,
                subscription_type_id: subscriptionTypeId
            })
        });
        
        if (response.ok) {
            showAlert('Абонемент успешно приобретён! Теперь вы можете записаться на занятие.');
            document.querySelector('.subscription-modal')?.remove();
            // Принудительно обновляем список занятий
            await loadClasses(userId);
        } else {
            throw new Error('Ошибка при покупке абонемента');
        }
    } catch (error) {
        console.error('Purchase error:', error);
        showAlert('Ошибка при покупке абонемента: ' + error.message);
    }
}

async function handleBooking(classId, userId) {
    try {
        // Дополнительная проверка на клиенте
        const classResponse = await fetch(`/api/class/${classId}`);
        if (!classResponse.ok) throw new Error('Не удалось получить данные о занятии');
        
        const classData = await classResponse.json();
        const classDate = new Date(classData.datetime);
        
        if (classDate < new Date()) {
            throw new Error('Нельзя записаться на прошедшее занятие');
        }
        
        const response = await fetch('/api/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, class_id: classId })
        });
        
        if (response.ok) {
            await loadClasses(userId);
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Ошибка записи');
        }
    } catch (error) {
        console.error('Booking error:', error);
        showAlert(error.message);
    }
}


async function cancelBooking(bookingId, classId, userId) {
    try {
        // Дополнительная проверка на клиенте
        const classResponse = await fetch(`/api/class/${classId}`);
        if (!classResponse.ok) throw new Error('Не удалось получить данные о занятии');
        
        const classData = await classResponse.json();
        const classDate = new Date(classData.datetime);
        
        if (classDate < new Date()) {
            throw new Error('Нельзя отменить прошедшее занятие');
        }
        
        const response = await fetch('/api/cancel_booking', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ booking_id: bookingId, user_id: userId })
        });
        
        if (response.ok) {
            await loadClasses(userId); // Обновляем список
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Ошибка отмены записи');
        }
    } catch (error) {
        console.error('Cancel booking error:', error);
        showAlert(error.message);
    }
}

function showAlert(message) {
//    if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
//        Telegram.WebApp.showAlert(message);
//    } else {
//        alert(message);
//    }
    alert(message);
}


function showError(message) {
    document.body.innerHTML = `
        <div class="error-container">
            <p>Ошибка загрузки: ${message}</p>
            <button onclick="location.reload()">Попробовать снова</button>
        </div>
    `;
}
