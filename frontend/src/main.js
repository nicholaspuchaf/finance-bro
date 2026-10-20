import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';
import './dark-theme.css';

mount(App, { target: document.getElementById('app') });
