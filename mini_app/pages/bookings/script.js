// Переключатель для тестового режима
const TEST_MODE = false;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
            Telegram.WebApp.expand();
            const userId = Telegram.WebApp.initDataUnsafe?.user?.id || 470064868;
            await loadBookings(userId);
            Telegram.WebApp.ready();
        } else {
            console.warn('Telegram WebApp API not available - running in browser mode');
            await loadBookings(470064868);
        }
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    }
});

// Тестовые данные
const TEST_BOOKINGS = [
    {
        id: 1,
        class_id: 1,
        class_name: "Йога для начинающих",
        datetime: new Date(Date.now() + 86400000).toISOString(), // Завтра
        description: "Базовые асаны для новичков",
        price: 800,
        can_cancel: true
    },
    {
        id: 2,
        class_id: 2,
        class_name: "Продвинутая йога",
        datetime: new Date(Date.now() - 86400000).toISOString(), // Вчера
        description: "Сложные асаны для опытных",
        price: 1000,
        can_cancel: false
    }
];

async function loadBookings(userId) {
    let bookings;
    
    if (TEST_MODE) {
        bookings = TEST_BOOKINGS;
    } else {
        try {
            const response = await fetch(`/api/user/bookings?user_id=${userId}`);
            if (!response.ok) throw new Error('Failed to load bookings');
            bookings = await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            showError('Ошибка загрузки записей');
            return;
        }
    }

    renderBookings(bookings);
}


function renderBookings(bookings) {
    console.log(bookings)
    const container = document.querySelector('.bookings-container');
    container.innerHTML = `
        <a href="/" class="back-button">← На главную</a>
        <h1 class="bookings-title">📝 Мои записи</h1>
        <div class="bookings-list" id="bookings-list"></div>
    `;
    
    const list = document.getElementById('bookings-list');
    
    if (!bookings || bookings.length === 0) {
        list.innerHTML = `
            <div class="no-bookings">
                <p>У вас нет активных записей</p>
                <a href="/schedule" class="action-button">Посмотреть расписание</a>
            </div>
        `;
        return;
    }
    
    bookings.forEach(booking => {
        const classDate = new Date(booking.class_datetime);
        const isPast = classDate < new Date();
        
        const card = document.createElement('div');
        card.className = 'booking-card';
        card.innerHTML = `
            <div class="booking-header">
                <h3 class="booking-name">${booking.class_name}</h3>
            </div>
            <span class="booking-status">${isPast ? 'Прошло' : 'Запланировано'}</span>
            <div class="booking-details">
                <p>${booking.description}</p>
                <div class="booking-time">
                    <i class="far fa-calendar-alt"></i>
                    <span>${classDate.toLocaleString()}</span>
                </div>
                <div class="booking-time">
                    <i class="fas fa-ruble-sign"></i>
                    <span>${booking.price} ₽</span>
                </div>
            </div>
            <div class="booking-actions">
                <button class="cancel-button" 
                    onclick="cancelBooking(${booking.id}, ${booking.user_id || 470064868})"
                    ${isPast ? 'disabled' : ''}>
                    Отменить запись
                </button>
            </div>
        `;
        list.appendChild(card);
    });

}


async function cancelBooking(bookingId, userId) {
    try {
        console.log(bookingId)
        const response = await fetch('/api/cancel_booking', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ 
                booking_id: bookingId, 
                user_id: userId 
            })
        });
        
        
        if (response.ok) {
            // Обновляем список без перезагрузки страницы
            if (TEST_MODE) {
                // Удаляем из тестовых данных
                const index = TEST_BOOKINGS.findIndex(b => b.id === bookingId);
                if (index !== -1) TEST_BOOKINGS.splice(index, 1);
                renderBookings(TEST_BOOKINGS);
            } else {
                await loadBookings(userId);
            }
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
    const container = document.querySelector('.bookings-container');
    container.innerHTML = `
        <div class="error-container">
            <p>${message}</p>
            <button onclick="location.reload()" class="action-button">Попробовать снова</button>
        </div>
    `;
}

