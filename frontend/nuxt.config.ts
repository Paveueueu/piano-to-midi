import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: ['@nuxt/eslint', '@nuxt/fonts', '@nuxtjs/i18n'],

  // Language from the browser, then a cookie; URLs are the same in both.
  i18n: {
    strategy: 'no_prefix',
    defaultLocale: 'en',
    locales: [
      { code: 'en', language: 'en-GB', name: 'English', file: 'en.json' },
      { code: 'pl', language: 'pl-PL', name: 'Polski', file: 'pl.json' },
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'piano-to-midi-lang',
      fallbackLocale: 'en',
    },
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      // The FastAPI backend. Override with NUXT_PUBLIC_API_BASE.
      apiBase: 'http://localhost:8100',
    },
  },

  vite: {
    plugins: [tailwindcss()],
  },

  app: {
    head: {
      title: 'Piano to MIDI',
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' }],
    },
  },

  fonts: {
    families: [{ name: 'Geist', provider: 'google', weights: [400, 500, 600, 700] }],
  },

  typescript: {
    strict: true,
  },
})
