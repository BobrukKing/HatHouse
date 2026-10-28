from urllib.parse import urlencode

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

try:
    import dns.resolver
except ImportError:  # pragma: no cover
    dns = None

User = get_user_model()


def email_is_valid_and_domain_exists(email):
    if not email:
        return False
    email = email.strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return False

    if "@" not in email:
        return False

    _, domain = email.rsplit("@", 1)
    if not domain or domain.startswith(".") or domain.endswith("."):
        return False

    if dns is None:
        return True

    try:
        answers = dns.resolver.resolve(domain, "MX")
        return bool(answers)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return False


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "auth-input",
            "placeholder": "example@gmail.com",
            "autocomplete": "email",
        }),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Ім’я користувача"
        self.fields["username"].widget.attrs.update({
            "class": "auth-input",
            "placeholder": "Ваше ім’я користувача",
            "autocomplete": "username",
        })
        self.fields["password1"].label = "Пароль"
        self.fields["password1"].widget.attrs.update({
            "class": "auth-input",
            "placeholder": "Створіть пароль",
            "autocomplete": "new-password",
        })
        self.fields["password2"].label = "Повторіть пароль"
        self.fields["password2"].widget.attrs.update({
            "class": "auth-input",
            "placeholder": "Повторіть пароль",
            "autocomplete": "new-password",
        })

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email_is_valid_and_domain_exists(email):
            raise forms.ValidationError("Введіть справжню пошту з існуючим доменом, наприклад user@gmail.com.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Користувач з такою поштою вже зареєстрований.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Користувач з таким іменем вже існує.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        label="ПІБ",
        max_length=180,
        widget=forms.TextInput(attrs={"class": "checkout-input", "autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "checkout-input", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Номер телефону",
        max_length=30,
        widget=forms.TelInput(attrs={"class": "checkout-input", "autocomplete": "tel"}),
    )
    delivery_address = forms.CharField(
        label="Адреса доставки або відділення пошти",
        max_length=500,
        widget=forms.Textarea(attrs={
            "class": "checkout-input",
            "autocomplete": "street-address",
            "rows": 3,
        }),
    )

    def clean_full_name(self):
        value = " ".join(self.cleaned_data["full_name"].split())
        if len(value.split()) < 2:
            raise forms.ValidationError("Вкажіть ім’я та прізвище.")
        return value

    def clean_phone(self):
        value = self.cleaned_data["phone"].strip()
        if sum(character.isdigit() for character in value) < 7:
            raise forms.ValidationError("Вкажіть коректний номер телефону.")
        return value

    def clean_delivery_address(self):
        return self.cleaned_data["delivery_address"].strip()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email або ім’я користувача",
        widget=forms.TextInput(attrs={
            "class": "auth-input",
            "placeholder": "example@gmail.com",
            "autocomplete": "username",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].label = "Пароль"
        self.fields["password"].widget.attrs.update({
            "class": "auth-input",
            "placeholder": "Ваш пароль",
            "autocomplete": "current-password",
        })

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            user = authenticate(request=self.request, username=username, password=password)
            if user is None:
                raise forms.ValidationError("Невірна пошта або пароль.")
            self.user_cache = user
            self.confirm_login_allowed(user)

        return self.cleaned_data
