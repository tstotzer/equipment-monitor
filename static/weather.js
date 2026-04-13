const form = document.getElementById('weather-form');
const cityInput = document.getElementById('city');
const message = document.getElementById('message');
const weatherResult = document.getElementById('weather-result');
const weatherLocation = document.getElementById('weather-location');
const weatherDescription = document.getElementById('weather-description');
const weatherIcon = document.getElementById('weather-icon');
const weatherTemperature = document.getElementById('weather-temperature');
const weatherFeels = document.getElementById('weather-feels');
const weatherHumidity = document.getElementById('weather-humidity');

const showMessage = (text, type = 'info') => {
  message.textContent = text;
  message.className = `message ${type}`;
};

const showResult = data => {
  weatherLocation.textContent = `${data.city}${data.country ? `, ${data.country}` : ''}`;
  weatherDescription.textContent = data.description;
  weatherTemperature.textContent = `${data.temperature.toFixed(1)}°C`;
  weatherFeels.textContent = `${data.feels_like.toFixed(1)}°C`;
  weatherHumidity.textContent = `${data.humidity}%`;
  weatherIcon.src = data.icon_url;
  weatherIcon.alt = data.description;
  weatherResult.classList.remove('hidden');
};

const fetchWeather = async city => {
  showMessage('Loading weather...', 'info');
  weatherResult.classList.add('hidden');

  try {
    const response = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
    const data = await response.json();

    if (!response.ok) {
      showMessage(data.error || 'Unable to load weather.', 'error');
      return;
    }

    showMessage('Weather loaded.', 'success');
    showResult(data);
  } catch (error) {
    showMessage('Network error. Try again.', 'error');
    console.error(error);
  }
};

form.addEventListener('submit', event => {
  event.preventDefault();
  const city = cityInput.value.trim();
  if (!city) {
    showMessage('Please enter a city name.', 'error');
    return;
  }
  fetchWeather(city);
});
