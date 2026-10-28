const productCategories = [
  'Winter Sale',
  'Берети',
  'Капори та балаклави',
  'Картузи',
  'Літня колекція'
];

const initialProducts = [
  {
    id: 1,
    category: 'Winter Sale',
    name: 'Santorini з широким полем пудрова',
    oldPrice: 1200,
    price: 890,
    image: 'images/1.png',
    gallery: ['images/1.png', 'images/2.png', 'images/3.png', 'images/4.png'],
    description: 'Модель з м’якого вовняного полотна, об’ємною формою та широким полем. Ідеально підходить для холодного сезону і доповнить будь-який образ.'
  },
  {
    id: 2,
    category: 'Берети',
    name: 'Milan Beige з елегантним підбором',
    oldPrice: 1100,
    price: 820,
    image: 'images/2.png',
    gallery: ['images/2.png', 'images/1.png', 'images/3.png', 'images/4.png'],
    description: 'Класичний берето з натуральної вовни та м’якою підкладкою. Підходить для повсякденного носіння та особливих заходів.'
  },
  {
    id: 3,
    category: 'Капори та балаклави',
    name: 'Velvet Noir капор з утепленням',
    oldPrice: 1350,
    price: 990,
    image: 'images/3.png',
    gallery: ['images/3.png', 'images/2.png', 'images/1.png', 'images/4.png'],
    description: 'Комфортний капор для активних зимових прогулянок. М’яке утеплення, гладка текстура та практичний крій зберігають тепло.'
  },
  {
    id: 4,
    category: 'Картузи',
    name: 'Cypress клубний картуз',
    oldPrice: 980,
    price: 760,
    image: 'images/4.png',
    gallery: ['images/4.png', 'images/1.png', 'images/2.png', 'images/3.png'],
    description: 'Картуз з високою посадкою, створений для стильного образу в холодну пору. Тверда форма та натуральний матеріал надають вишуканості.'
  },
  {
    id: 5,
    category: 'Літня колекція',
    name: 'Aster літній панама',
    oldPrice: 780,
    price: 590,
    image: 'images/3.png',
    gallery: ['images/3.png', 'images/4.png', 'images/1.png', 'images/2.png'],
    description: 'Легка панама для сонячних днів із натуральною лляною фактурою. Підходить для відпочинку, міських прогулянок та відпустки.'
  }
];

const products = [...initialProducts];
