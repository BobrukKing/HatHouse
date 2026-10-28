const catalogState = {
  page: 1,
  itemsPerPage: 5,
  category: 'all',
};

const STORAGE_KEY = 'hatshop_products';
const CATEGORIES_STORAGE_KEY = 'hatshop_categories';
const SITE_SETTINGS_STORAGE_KEY = 'hatshop_site_settings';
const MAX_CATEGORIES = 16;
const MAX_CATEGORY_NAME_LENGTH = 15;
const CATEGORY_LIMIT_MESSAGE = 'Неможливо додати більше 16 категорій. Змініть або видаліть існуючу категорію.';
const CATEGORY_NAME_LIMIT_MESSAGE = 'Назва категорії не може перевищувати 15 символів.';
const defaultSiteSettings = {
  seasonText: 'Осінь / Зима 2026',
  brandName: 'HatHouse',
  brandImage: '',
};
let siteSettings = { ...defaultSiteSettings };
let pendingCategoryDeletion = null;

function restoreSiteSettings() {
  const raw = localStorage.getItem(SITE_SETTINGS_STORAGE_KEY);
  if (!raw) return;

  try {
    const savedSettings = JSON.parse(raw);
    siteSettings = { ...defaultSiteSettings, ...savedSettings };
  } catch (error) {
    console.warn('Не вдалося прочитати налаштування оформлення:', error);
  }
}

function saveSiteSettings() {
  localStorage.setItem(SITE_SETTINGS_STORAGE_KEY, JSON.stringify(siteSettings));
}

function renderSiteSettings() {
  const seasonText = document.getElementById('season-text');
  const brandText = document.getElementById('brand-text');
  const brandMark = document.getElementById('brand-mark');
  const footerBrand = document.getElementById('footer-brand');

  if (seasonText) seasonText.textContent = siteSettings.seasonText;
  if (brandText) brandText.textContent = siteSettings.brandName;
  if (footerBrand) footerBrand.textContent = siteSettings.brandName;
  if (brandMark) {
    if (siteSettings.brandImage) {
      brandMark.textContent = '';
      brandMark.style.backgroundImage = `url("${siteSettings.brandImage}")`;
      brandMark.classList.add('has-image');
    } else {
      brandMark.textContent = siteSettings.brandName.charAt(0).toUpperCase();
      brandMark.style.backgroundImage = '';
      brandMark.classList.remove('has-image');
    }
  }
}

function getCatalogTitle() {
  return catalogState.category === 'all' ? 'Каталог головних уборів' : `Каталог: ${catalogState.category}`;
}

function renderCatalogHeading() {
  const title = document.getElementById('catalog-title');
  if (title) title.textContent = getCatalogTitle();
}

function saveCategoriesToStorage() {
  localStorage.setItem(CATEGORIES_STORAGE_KEY, JSON.stringify(productCategories));
}

function restoreCategoriesFromStorage() {
  const raw = localStorage.getItem(CATEGORIES_STORAGE_KEY);

  if (!raw) {
    saveCategoriesToStorage();
    return;
  }

  try {
    const savedCategories = JSON.parse(raw);
    if (Array.isArray(savedCategories)) {
      productCategories.splice(0, productCategories.length, ...savedCategories.filter((category) => typeof category === 'string' && category.trim()));
    }
  } catch (error) {
    console.warn('Не вдалося прочитати категорії з localStorage:', error);
  }
}

function saveProductsToStorage() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(products));
}

function restoreProductsFromStorage() {
  const raw = localStorage.getItem(STORAGE_KEY);

  if (!raw) {
    saveProductsToStorage();
    return;
  }

  try {
    const savedProducts = JSON.parse(raw);

    if (Array.isArray(savedProducts)) {
      products.splice(0, products.length, ...savedProducts);
    }
  } catch (error) {
    console.warn('Не вдалося прочитати товари з localStorage:', error);
  }
}

function formatPrice(value) {
  return `${value.toLocaleString('uk-UA')} грн`;
}

function renderPriceMarkup(product) {
  const oldPrice = Number(product.oldPrice);
  const price = Number(product.price);
  const oldPriceMarkup = oldPrice > price ? `<span class="old-price">${formatPrice(oldPrice)}</span>` : '';

  return `${oldPriceMarkup}<span class="new-price">${formatPrice(price)}</span>`;
}

function generateGalleryFromImage(imageSrc) {
  if (!imageSrc) {
    return ['images/1.png', 'images/2.png', 'images/3.png', 'images/4.png'];
  }

  return [imageSrc, 'images/1.png', 'images/2.png', 'images/3.png'];
}

function getFilteredProducts() {
  if (catalogState.category === 'all') {
    return products;
  }

  return products.filter((product) => product.category === catalogState.category);
}

function renderCatalog() {
  const grid = document.getElementById('product-grid');
  if (!grid) return;

  const filteredProducts = getFilteredProducts();
  const totalPages = Math.max(1, Math.ceil(filteredProducts.length / catalogState.itemsPerPage));
  const safePage = Math.min(catalogState.page, totalPages);
  catalogState.page = safePage;

  const startIndex = (safePage - 1) * catalogState.itemsPerPage;
  const currentProducts = filteredProducts.slice(startIndex, startIndex + catalogState.itemsPerPage);

  grid.innerHTML = currentProducts
    .map(
      (product) => `
        <article class="product-card">
          <a href="product.html?id=${product.id}" aria-label="Перейти до товару ${product.name}">
            <img class="product-image" src="${product.image}" alt="${product.name}" />
          </a>
          <div class="product-body">
            <span class="product-category">${product.category}</span>
            <a href="product.html?id=${product.id}" class="product-name">${product.name}</a>
            <div class="price-row">
              ${renderPriceMarkup(product)}
            </div>
            <button class="add-to-cart" type="button" data-product-name="${product.name}">Додати у кошик</button>
          </div>
        </article>
      `
    )
    .join('');

  renderPagination(totalPages);
  bindCartButtons();
}

function renderPagination(totalPages) {
  const pagination = document.getElementById('pagination-numbers');
  if (!pagination) return;

  const pages = Array.from({ length: totalPages }, (_, index) => index + 1);
  pagination.innerHTML = pages
    .map(
      (page) => `
        <button
          class="page-number ${page === catalogState.page ? 'active' : ''}"
          type="button"
          data-page="${page}"
          aria-label="Перейти на сторінку ${page}"
        >
          ${page}
        </button>
      `
    )
    .join('');

  pagination.querySelectorAll('.page-number').forEach((button) => {
    button.addEventListener('click', () => {
      catalogState.page = Number(button.dataset.page);
      renderCatalog();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

function updateActiveCategoryLinks() {
  document.querySelectorAll('.category-link').forEach((link) => {
    const isActive = link.dataset.category === catalogState.category;
    link.classList.toggle('active', isActive);
  });
  renderCatalogHeading();
}

function populateCategorySelect() {
  const categorySelect = document.querySelector('#product-form select[name="category"]');
  if (!categorySelect) return;

  categorySelect.innerHTML = productCategories
    .map((category) => `<option value="${category}">${category}</option>`)
    .join('');
}

function renderCategoryNavigation() {
  const navigation = document.querySelector('.main-nav');
  if (!navigation) return;

  navigation.querySelectorAll('.category-nav-links').forEach((links) => links.remove());
  navigation.querySelectorAll('.category-link:not([data-category="all"])').forEach((link) => link.remove());
  let allLink = navigation.querySelector('[data-category="all"]');
  const managerButton = document.getElementById('category-manager-toggle');
  if (!allLink) {
    allLink = document.createElement('a');
    allLink.href = 'index.html?category=all';
    allLink.className = 'category-link category-link-all';
    allLink.dataset.category = 'all';
    allLink.textContent = 'Всі товари';
    navigation.prepend(allLink);
  }

  const categoryLinks = document.createElement('div');
  categoryLinks.className = 'category-nav-links';
  [productCategories.slice(0, 8), productCategories.slice(8)].forEach((rowCategories) => {
    if (!rowCategories.length) return;
    const row = document.createElement('div');
    row.className = 'category-nav-row';
    rowCategories.forEach((category) => {
      const link = document.createElement('a');
      link.href = `index.html?category=${encodeURIComponent(category)}`;
      link.className = 'category-link';
      link.dataset.category = category;
      link.textContent = category;
      row.append(link);
    });
    categoryLinks.append(row);
  });
  navigation.insertBefore(categoryLinks, managerButton);

  updateActiveCategoryLinks();
  populateCategorySelect();
}

function renderCategoryManager() {
  const list = document.getElementById('category-manager-list');
  if (!list) return;

  list.innerHTML = productCategories
    .map(
      (category) => `
        <div class="category-manager-row">
          <input type="text" value="${category}" maxlength="${MAX_CATEGORY_NAME_LENGTH}" data-category-input="${category}" aria-label="Назва категорії ${category}" />
          <button type="button" class="rename-category-button" data-category="${category}">Зберегти</button>
          <button type="button" class="remove-category-button" data-category="${category}" aria-label="Видалити категорію ${category}">×</button>
        </div>
      `
    )
    .join('');

  list.querySelectorAll('.rename-category-button').forEach((button) => {
    button.addEventListener('click', () => {
      const input = list.querySelector(`[data-category-input="${CSS.escape(button.dataset.category)}"]`);
      renameCategory(button.dataset.category, input.value);
    });
  });

  list.querySelectorAll('.remove-category-button').forEach((button) => {
    button.addEventListener('click', () => removeCategory(button.dataset.category));
  });
}

function renameCategory(oldName, nextName) {
  const trimmedName = String(nextName || '').trim();
  if (trimmedName === oldName) return;
  if (!trimmedName) {
    alert('Введіть назву категорії.');
    return;
  }
  if (Array.from(trimmedName).length > MAX_CATEGORY_NAME_LENGTH) {
    alert(CATEGORY_NAME_LIMIT_MESSAGE);
    return;
  }
  if (productCategories.some((category) => category !== oldName && category.toLowerCase() === trimmedName.toLowerCase())) {
    alert('Така категорія вже існує.');
    return;
  }

  const categoryIndex = productCategories.indexOf(oldName);
  if (categoryIndex === -1) return;
  productCategories[categoryIndex] = trimmedName;
  products.forEach((product) => {
    if (product.category === oldName) product.category = trimmedName;
  });
  if (catalogState.category === oldName) catalogState.category = trimmedName;
  saveCategoriesToStorage();
  saveProductsToStorage();
  renderCategoryNavigation();
  renderCategoryManager();
  renderCatalog();
}

function removeCategory(categoryToRemove) {
  const categoryIndex = productCategories.indexOf(categoryToRemove);
  if (categoryIndex === -1) return;
  const categoryProducts = products.filter((product) => product.category === categoryToRemove);

  if (categoryProducts.length > 0) {
    pendingCategoryDeletion = categoryToRemove;
    const modal = document.getElementById('category-delete-modal');
    const message = document.getElementById('category-delete-message');
    message.textContent = `У категорії «${categoryToRemove}» є ${categoryProducts.length} товар(ів). Після підтвердження категорію та всі ці товари буде видалено.`;
    modal.classList.remove('hidden');
    return;
  }

  deleteCategoryAndProducts(categoryToRemove);
}

function deleteCategoryAndProducts(categoryToRemove) {
  const categoryIndex = productCategories.indexOf(categoryToRemove);
  if (categoryIndex === -1) return;

  productCategories.splice(categoryIndex, 1);
  for (let index = products.length - 1; index >= 0; index -= 1) {
    if (products[index].category === categoryToRemove) products.splice(index, 1);
  }
  if (catalogState.category === categoryToRemove) catalogState.category = 'all';
  saveCategoriesToStorage();
  saveProductsToStorage();
  renderCategoryNavigation();
  renderCategoryManager();
  renderCatalog();
}

function initCategoryManager() {
  const manager = document.getElementById('category-manager');
  const toggle = document.getElementById('category-manager-toggle');
  const close = document.getElementById('close-category-manager');
  const addForm = document.getElementById('category-add-form');
  const deleteModal = document.getElementById('category-delete-modal');
  const cancelDelete = document.getElementById('cancel-category-delete');
  const confirmDelete = document.getElementById('confirm-category-delete');
  if (!manager || !toggle || !close || !addForm) return;

  renderCategoryManager();
  toggle.addEventListener('click', () => manager.classList.toggle('hidden'));
  close.addEventListener('click', () => manager.classList.add('hidden'));
  cancelDelete.addEventListener('click', () => {
    pendingCategoryDeletion = null;
    deleteModal.classList.add('hidden');
  });
  confirmDelete.addEventListener('click', () => {
    if (!pendingCategoryDeletion) return;
    const categoryToRemove = pendingCategoryDeletion;
    pendingCategoryDeletion = null;
    deleteModal.classList.add('hidden');
    deleteCategoryAndProducts(categoryToRemove);
  });
  deleteModal.addEventListener('click', (event) => {
    if (event.target === deleteModal) cancelDelete.click();
  });
  addForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const nameInput = addForm.elements.categoryName;
    const newCategory = String(nameInput.value || '').trim();
    if (!newCategory) return;
    if (Array.from(newCategory).length > MAX_CATEGORY_NAME_LENGTH) {
      alert(CATEGORY_NAME_LIMIT_MESSAGE);
      return;
    }
    if (productCategories.some((category) => category.toLowerCase() === newCategory.toLowerCase())) {
      alert('Така категорія вже існує.');
      return;
    }
    if (productCategories.length >= MAX_CATEGORIES) {
      alert(CATEGORY_LIMIT_MESSAGE);
      return;
    }
    productCategories.push(newCategory);
    saveCategoriesToStorage();
    renderCategoryNavigation();
    renderCategoryManager();
    addForm.reset();
  });
}

function initSiteSettings() {
  const modal = document.getElementById('site-settings-modal');
  const form = document.getElementById('site-settings-form');
  const seasonButton = document.getElementById('season-edit-button');
  const brandButton = document.getElementById('brand-edit-button');
  const closeButton = document.getElementById('close-site-settings');
  const cancelButton = document.getElementById('cancel-site-settings');
  if (!modal || !form || !seasonButton || !brandButton || !closeButton || !cancelButton) return;

  const openSettings = () => {
    form.elements.seasonText.value = siteSettings.seasonText;
    form.elements.brandName.value = siteSettings.brandName;
    form.elements.brandImage.value = '';
    modal.classList.remove('hidden');
  };
  const closeSettings = () => modal.classList.add('hidden');

  seasonButton.addEventListener('click', openSettings);
  brandButton.addEventListener('click', openSettings);
  closeButton.addEventListener('click', closeSettings);
  cancelButton.addEventListener('click', closeSettings);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeSettings();
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const uploadedImage = formData.get('brandImage');
    const previousSettings = { ...siteSettings };

    siteSettings.seasonText = String(formData.get('seasonText') || defaultSiteSettings.seasonText).trim();
    siteSettings.brandName = String(formData.get('brandName') || defaultSiteSettings.brandName).trim();
    if (uploadedImage instanceof File && uploadedImage.size > 0) {
      try {
        siteSettings.brandImage = await readBrandImageAsDataUrl(uploadedImage);
      } catch (error) {
        siteSettings = previousSettings;
        alert('Не вдалося обробити зображення аватарки. Спробуйте інше фото.');
        return;
      }
    }
    try {
      saveSiteSettings();
    } catch (error) {
      siteSettings = previousSettings;
      alert('Не вдалося зберегти налаштування. Спробуйте зображення меншого розміру.');
      return;
    }
    renderSiteSettings();
    closeSettings();
  });
}

function getEditablePageElements() {
  const page = document.querySelector('[data-editable-page]');
  const content = document.getElementById('editable-page-content');
  if (!page || !content) return null;

  return {
    pageName: page.dataset.editablePage,
    content,
    storageKey: `hatshop_page_content_${page.dataset.editablePage}`,
  };
}

function renderStoredPageContent() {
  const page = getEditablePageElements();
  if (!page) return;

  const raw = localStorage.getItem(page.storageKey);
  if (!raw) return;

  try {
    const paragraphs = JSON.parse(raw);
    if (!Array.isArray(paragraphs)) return;

    page.content.replaceChildren();
    paragraphs.filter((text) => typeof text === 'string').forEach((text) => {
      const paragraph = document.createElement('p');
      if (page.pageName === 'contacts' && text.includes(':')) {
        const separatorIndex = text.indexOf(':');
        const label = document.createElement('strong');
        label.textContent = text.slice(0, separatorIndex + 1);
        paragraph.append(label, document.createTextNode(text.slice(separatorIndex + 1).trimStart()));
      } else {
        paragraph.textContent = text;
      }
      page.content.append(paragraph);
    });
  } catch (error) {
    console.warn('Не вдалося прочитати текст сторінки:', error);
  }
}

function initEditablePageContent() {
  const page = getEditablePageElements();
  const form = document.getElementById('page-content-editor');
  const editButton = document.getElementById('edit-page-content');
  const cancelButton = document.getElementById('cancel-page-content');
  const input = document.getElementById('page-content-input');
  if (!page || !form || !editButton || !cancelButton || !input) return;

  renderStoredPageContent();
  editButton.addEventListener('click', () => {
    input.value = Array.from(page.content.querySelectorAll('p'), (paragraph) => paragraph.textContent.trim()).join('\n');
    form.classList.remove('hidden');
    input.focus();
  });
  cancelButton.addEventListener('click', () => form.classList.add('hidden'));
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const paragraphs = input.value.split(/\r?\n/).map((text) => text.trim()).filter(Boolean);
    if (paragraphs.length === 0) {
      alert('Додайте хоча б один абзац.');
      return;
    }

    try {
      localStorage.setItem(page.storageKey, JSON.stringify(paragraphs));
      renderStoredPageContent();
      form.classList.add('hidden');
    } catch (error) {
      alert('Не вдалося зберегти текст сторінки.');
    }
  });
}

function renderProductDetail() {
  const container = document.getElementById('product-detail');
  if (!container) return;

  const params = new URLSearchParams(window.location.search);
  const productId = Number(params.get('id')) || 1;
  const product = products.find((item) => item.id === productId) || products[0];
  if (!product) {
    container.innerHTML = '<p class="info-card">Товарів у каталозі поки немає.</p>';
    return;
  }
  const gallery = product.gallery && product.gallery.length ? product.gallery : generateGalleryFromImage(product.image);
  const isAvailable = product.available !== false;

  container.innerHTML = `
    <div class="gallery-panel">
      <button class="photo-button" type="button" id="main-photo-button" aria-label="Відкрити фото ${product.name}">
        <img class="main-photo" src="${gallery[0]}" alt="${product.name}" id="main-product-image" />
      </button>
      <div class="thumbs">
        ${gallery
          .map(
            (image, index) => `
              <img
                class="thumb ${index === 0 ? 'active' : ''}"
                src="${image}"
                alt="${product.name} фото ${index + 1}"
                data-image="${image}"
              />
            `
          )
          .join('')}
      </div>
    </div>

    <div class="image-modal hidden" id="image-modal" role="dialog" aria-modal="true" aria-label="Перегляд фото">
      <button class="image-modal-close" type="button" id="image-modal-close" aria-label="Закрити фото">×</button>
      <img class="image-modal-photo" id="image-modal-photo" src="${gallery[0]}" alt="${product.name}" />
    </div>

    <div class="product-info">
      <div class="product-meta-line">
        <span class="product-category">${product.category}</span>
      </div>
      <h1>${product.name}</h1>
      <span class="stock ${isAvailable ? '' : 'out-of-stock'}">${isAvailable ? 'В наявності' : 'Немає в наявності'}</span>
      <div class="detail-price">
        ${renderPriceMarkup(product)}
      </div>
      <div class="product-actions">
        <button class="add-to-cart" type="button" data-product-name="${product.name}" ${isAvailable ? '' : 'disabled'}>Додати у кошик</button>
        <button class="edit-product-button" type="button" id="edit-product-button">Редагувати товар</button>
        <button class="delete-product-button" type="button" id="delete-product-button">Видалити товар</button>
      </div>

      <form class="edit-product-form hidden" id="edit-product-form">
        <label>
          Назва товару
          <input type="text" name="name" value="${product.name}" required />
        </label>
        <label>
          Ціна продажу, грн
          <input type="number" name="price" min="1" step="1" value="${product.price}" required />
        </label>
        <label>
          Стара ціна, грн (якщо є знижка)
          <input type="number" name="oldPrice" min="1" step="1" value="${product.oldPrice || ''}" />
        </label>
        <label>
          Опис товару
          <textarea name="description" rows="4" required>${product.description}</textarea>
        </label>
        <label class="availability-control">
          <input type="checkbox" name="available" ${isAvailable ? 'checked' : ''} />
          В наявності
        </label>
        <div class="edit-form-actions">
          <button class="submit-product" type="submit">Зберегти зміни</button>
          <button class="cancel-edit-button" type="button" id="cancel-edit-button">Скасувати</button>
        </div>
      </form>

      <div class="product-description">
        <h2>Опис</h2>
        <p>${product.description}</p>
      </div>
    </div>
  `;

  const mainImage = document.getElementById('main-product-image');
  const thumbs = document.querySelectorAll('.thumb');
  const imageModal = document.getElementById('image-modal');
  const modalImage = document.getElementById('image-modal-photo');

  const openImageModal = () => {
    modalImage.src = mainImage.src;
    imageModal.classList.remove('hidden');
  };

  const closeImageModal = () => imageModal.classList.add('hidden');

  document.getElementById('main-photo-button').addEventListener('click', openImageModal);
  document.getElementById('image-modal-close').addEventListener('click', closeImageModal);
  imageModal.addEventListener('click', (event) => {
    if (event.target === imageModal) closeImageModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeImageModal();
  });

  thumbs.forEach((thumb) => {
    thumb.addEventListener('click', () => {
      const { image } = thumb.dataset;
      mainImage.src = image;
      modalImage.src = image;
      thumbs.forEach((item) => item.classList.toggle('active', item === thumb));
      openImageModal();
    });
  });

  initProductEditing(product);
  bindCartButtons();
}

function initProductEditing(product) {
  const editButton = document.getElementById('edit-product-button');
  const deleteButton = document.getElementById('delete-product-button');
  const editForm = document.getElementById('edit-product-form');
  const cancelButton = document.getElementById('cancel-edit-button');

  editButton.addEventListener('click', () => {
    editForm.classList.remove('hidden');
    editButton.classList.add('hidden');
  });

  cancelButton.addEventListener('click', () => {
    editForm.classList.add('hidden');
    editButton.classList.remove('hidden');
  });

  editForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const formData = new FormData(editForm);
    product.name = String(formData.get('name') || '').trim();
    product.price = Number(formData.get('price')) || 0;
    product.oldPrice = Number(formData.get('oldPrice')) || null;
    product.description = String(formData.get('description') || '').trim();
    product.available = formData.get('available') === 'on';
    saveProductsToStorage();
    renderProductDetail();
    alert('Зміни товару збережено');
  });

  deleteButton.addEventListener('click', () => {
    if (!window.confirm(`Видалити товар «${product.name}»?`)) return;

    const productIndex = products.findIndex((item) => item.id === product.id);
    if (productIndex !== -1) products.splice(productIndex, 1);
    saveProductsToStorage();
    window.location.href = 'index.html';
  });
}

function bindCartButtons() {
  document.querySelectorAll('.add-to-cart').forEach((button) => {
    if (button.disabled) return;
    button.addEventListener('click', () => {
      const productName = button.dataset.productName || 'Товар';
      alert(`${productName} додано у кошик`);
    });
  });
}

function initCatalogControls() {
  const itemsSelect = document.getElementById('items-per-page');
  if (!itemsSelect) return;

  itemsSelect.addEventListener('change', (event) => {
    catalogState.itemsPerPage = Number(event.target.value);
    catalogState.page = 1;
    renderCatalog();
  });
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const fileReader = new FileReader();

    fileReader.onload = () => resolve(fileReader.result);
    fileReader.onerror = () => reject(fileReader.error);
    fileReader.readAsDataURL(file);
  });
}

async function readBrandImageAsDataUrl(file) {
  const source = await readFileAsDataUrl(file);
  const image = new Image();
  await new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = reject;
    image.src = source;
  });

  const scale = Math.min(1, 512 / Math.max(image.naturalWidth, image.naturalHeight));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Не вдалося обробити зображення.');
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/webp', 0.82);
}

async function handleAddProduct(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const formData = new FormData(form);

  const uploadedFiles = formData.getAll('images').filter((file) => file instanceof File && file.size > 0);
  if (uploadedFiles.length < 4 || uploadedFiles.length > 10) {
    alert('Помилка: виберіть від 4 до 10 фотографій товару.');
    return;
  }

  try {
    const gallery = await Promise.all(uploadedFiles.map(readFileAsDataUrl));
    const newProduct = {
      id: Date.now(),
      category: formData.get('category') || 'Winter Sale',
      name: String(formData.get('name') || 'Новий товар').trim(),
      oldPrice: Number(formData.get('oldPrice')) || null,
      price: Number(formData.get('price') || 0),
      image: gallery[0],
      gallery,
      description: String(formData.get('description') || 'Опис товару').trim(),
      available: true,
    };

    products.unshift(newProduct);
    saveProductsToStorage();
    catalogState.page = 1;
    renderCatalog();
    form.reset();
    alert('Товар успішно додано до каталогу');
  } catch (error) {
    alert('Не вдалося завантажити фотографії. Спробуйте ще раз.');
  }
}

function initCategoryNavigation() {
  const navigation = document.querySelector('.main-nav');
  if (!navigation || !document.getElementById('product-grid')) return;

  const params = new URLSearchParams(window.location.search);
  const requestedCategory = params.get('category') || 'all';
  catalogState.category = requestedCategory === 'all' || productCategories.includes(requestedCategory) ? requestedCategory : 'all';

  navigation.addEventListener('click', (event) => {
    const link = event.target.closest('.category-link');
    if (!link || !navigation.contains(link)) return;

    event.preventDefault();
    const category = link.dataset.category || 'all';
    catalogState.category = category;
    catalogState.page = 1;
    updateActiveCategoryLinks();
    renderCatalog();
    window.history.replaceState({}, '', `index.html?category=${encodeURIComponent(category)}`);
  });

  updateActiveCategoryLinks();
}

function toggleAddProductPanel(forceOpen) {
  const panel = document.getElementById('add-product-section');
  const button = document.getElementById('floating-add-button');

  if (!panel || !button) return;

  const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : panel.classList.contains('hidden');
  panel.classList.toggle('hidden', !shouldOpen);
  button.textContent = shouldOpen ? '×' : '+';
  button.setAttribute('aria-label', shouldOpen ? 'Закрити форму додавання товару' : 'Додати товар');
}

document.addEventListener('DOMContentLoaded', () => {
  restoreSiteSettings();
  restoreCategoriesFromStorage();
  restoreProductsFromStorage();
  initCategoryNavigation();
  renderCategoryNavigation();
  renderCatalog();
  renderProductDetail();
  initCatalogControls();
  initCategoryManager();
  renderSiteSettings();
  initSiteSettings();
  initEditablePageContent();

  const productForm = document.getElementById('product-form');
  if (productForm) {
    productForm.addEventListener('submit', handleAddProduct);
  }

  const addButton = document.getElementById('floating-add-button');
  if (addButton) {
    addButton.addEventListener('click', () => {
      toggleAddProductPanel();
    });
  }
});

window.addEventListener('storage', (event) => {
  if (typeof event.key === 'string' && event.key.startsWith('hatshop_page_content_')) {
    renderStoredPageContent();
    return;
  }
  if (![STORAGE_KEY, CATEGORIES_STORAGE_KEY, SITE_SETTINGS_STORAGE_KEY].includes(event.key)) return;

  restoreSiteSettings();
  restoreCategoriesFromStorage();
  restoreProductsFromStorage();
  if (!productCategories.includes(catalogState.category)) catalogState.category = 'all';
  renderCategoryNavigation();
  renderCategoryManager();
  renderSiteSettings();
  renderCatalog();
  renderProductDetail();
});
