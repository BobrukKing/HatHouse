from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")

        if not username or not password:
            return None

        user_model = get_user_model()
        users = user_model.objects.filter(Q(username__iexact=username) | Q(email__iexact=username))

        for user in users:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model._default_manager.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
