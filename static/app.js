const display = document.getElementById('display');
const buttons = document.getElementById('buttons');

const updateDisplay = value => {
  display.value = value;
};

const appendValue = value => {
  if (value === 'C') {
    updateDisplay('');
    return;
  }

  if (value === '=') {
    calculateExpression(display.value);
    return;
  }

  updateDisplay(display.value + value);
};

const calculateExpression = async expression => {
  if (!expression.trim()) {
    return;
  }

  try {
    const encoded = encodeURIComponent(expression);
    const response = await fetch(`/api/calc?expression=${encoded}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Calculation failed');
    }

    updateDisplay(String(data.result));
  } catch (error) {
    updateDisplay('Error');
    console.error(error);
  }
};

buttons.addEventListener('click', event => {
  const target = event.target;
  if (target.matches('button')) {
    appendValue(target.dataset.value);
  }
});

window.addEventListener('keydown', event => {
  const allowedKeys = '0123456789.+-*/()';
  if (event.key === 'Enter') {
    event.preventDefault();
    calculateExpression(display.value);
  } else if (event.key === 'Backspace') {
    updateDisplay(display.value.slice(0, -1));
  } else if (event.key === 'Escape') {
    updateDisplay('');
  } else if (allowedKeys.includes(event.key)) {
    updateDisplay(display.value + event.key);
  }
});
