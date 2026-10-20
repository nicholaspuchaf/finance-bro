import { mount } from 'svelte';
import App from './App.svelte';
import { initializeI18n } from './i18n/index.js';
import './app.css';
import './dark-theme.css';

initializeI18n();
mount(App, { target: document.getElementById('app') });
