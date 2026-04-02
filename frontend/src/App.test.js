import { render } from '@testing-library/react';
import App from './app';

test('renders revAi workspace', () => {
  render(<App />);
  // Just check the app renders without crashing
  expect(document.body).toBeTruthy();
});