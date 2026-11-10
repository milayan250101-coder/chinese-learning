import type { VocabularyWord } from '../types'

export const vocabulary: VocabularyWord[] = [
  { id: 'hello', chinese: '你好', pinyin: 'nǐ hǎo', translations: { en: 'Hello', de: 'Hallo', fr: 'Bonjour', es: 'Hola', it: 'Ciao' }, category: 'greetings', image: null },
  { id: 'thank-you', chinese: '谢谢', pinyin: 'xièxie', translations: { en: 'Thank you', de: 'Danke', fr: 'Merci', es: 'Gracias', it: 'Grazie' }, category: 'greetings', image: null },
  { id: 'goodbye', chinese: '再见', pinyin: 'zàijiàn', translations: { en: 'Goodbye', de: 'Auf Wiedersehen', fr: 'Au revoir', es: 'Adiós', it: 'Arrivederci' }, category: 'greetings', image: null },
  { id: 'sorry', chinese: '对不起', pinyin: 'duìbuqǐ', translations: { en: 'Sorry', de: 'Entschuldigung', fr: 'Pardon', es: 'Lo siento', it: 'Mi dispiace' }, category: 'greetings', image: null },
  { id: 'please', chinese: '请', pinyin: 'qǐng', translations: { en: 'Please', de: 'Bitte', fr: "S'il vous plaît", es: 'Por favor', it: 'Per favore' }, category: 'greetings', image: null },
  { id: 'i', chinese: '我', pinyin: 'wǒ', translations: { en: 'I', de: 'Ich', fr: 'Je', es: 'Yo', it: 'Io' }, category: 'people', image: null },
  { id: 'you', chinese: '你', pinyin: 'nǐ', translations: { en: 'You', de: 'Du', fr: 'Tu', es: 'Tú', it: 'Tu' }, category: 'people', image: null },
  { id: 'we', chinese: '我们', pinyin: 'wǒmen', translations: { en: 'We', de: 'Wir', fr: 'Nous', es: 'Nosotros', it: 'Noi' }, category: 'people', image: null },
  { id: 'friend', chinese: '朋友', pinyin: 'péngyou', translations: { en: 'Friend', de: 'Freund', fr: 'Ami', es: 'Amigo', it: 'Amico' }, category: 'people', image: null },
  { id: 'family', chinese: '家人', pinyin: 'jiārén', translations: { en: 'Family', de: 'Familie', fr: 'Famille', es: 'Familia', it: 'Famiglia' }, category: 'people', image: null },
  { id: 'water', chinese: '水', pinyin: 'shuǐ', translations: { en: 'Water', de: 'Wasser', fr: 'Eau', es: 'Agua', it: 'Acqua' }, category: 'food', image: null },
  { id: 'tea', chinese: '茶', pinyin: 'chá', translations: { en: 'Tea', de: 'Tee', fr: 'Thé', es: 'Té', it: 'Tè' }, category: 'food', image: null },
  { id: 'rice', chinese: '米饭', pinyin: 'mǐfàn', translations: { en: 'Cooked rice', de: 'Gekochter Reis', fr: 'Riz cuit', es: 'Arroz cocido', it: 'Riso cotto' }, category: 'food', image: null },
  { id: 'coffee', chinese: '咖啡', pinyin: 'kāfēi', translations: { en: 'Coffee', de: 'Kaffee', fr: 'Café', es: 'Café', it: 'Caffè' }, category: 'food', image: null },
  { id: 'delicious', chinese: '好吃', pinyin: 'hǎochī', translations: { en: 'Delicious', de: 'Lecker', fr: 'Délicieux', es: 'Delicioso', it: 'Delizioso' }, category: 'food', image: null },
  { id: 'today', chinese: '今天', pinyin: 'jīntiān', translations: { en: 'Today', de: 'Heute', fr: "Aujourd'hui", es: 'Hoy', it: 'Oggi' }, category: 'time', image: null },
  { id: 'tomorrow', chinese: '明天', pinyin: 'míngtiān', translations: { en: 'Tomorrow', de: 'Morgen', fr: 'Demain', es: 'Mañana', it: 'Domani' }, category: 'time', image: null },
  { id: 'where', chinese: '哪里', pinyin: 'nǎli', translations: { en: 'Where', de: 'Wo', fr: 'Où', es: 'Dónde', it: 'Dove' }, category: 'travel', image: null },
  { id: 'restroom', chinese: '厕所', pinyin: 'cèsuǒ', translations: { en: 'Restroom', de: 'Toilette', fr: 'Toilettes', es: 'Baño', it: 'Bagno' }, category: 'travel', image: null },
  { id: 'station', chinese: '车站', pinyin: 'chēzhàn', translations: { en: 'Station', de: 'Bahnhof', fr: 'Gare', es: 'Estación', it: 'Stazione' }, category: 'travel', image: null },
  { id: 'how-much', chinese: '多少钱', pinyin: 'duōshǎo qián', translations: { en: 'How much?', de: 'Wie viel?', fr: 'Combien ?', es: '¿Cuánto cuesta?', it: 'Quanto costa?' }, category: 'travel', image: null },
  { id: 'like', chinese: '喜欢', pinyin: 'xǐhuan', translations: { en: 'To like', de: 'Mögen', fr: 'Aimer', es: 'Gustar', it: 'Piacere' }, category: 'everyday', image: null },
  { id: 'study', chinese: '学习', pinyin: 'xuéxí', translations: { en: 'To study', de: 'Lernen', fr: 'Étudier', es: 'Estudiar', it: 'Studiare' }, category: 'everyday', image: null },
  { id: 'good', chinese: '好', pinyin: 'hǎo', translations: { en: 'Good', de: 'Gut', fr: 'Bon', es: 'Bueno', it: 'Buono' }, category: 'everyday', image: null },
]

export function getTranslation(word: VocabularyWord, language: keyof VocabularyWord['translations']) {
  return word.translations[language]
}