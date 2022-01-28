from datetimeutc.fields import DateTimeUTCField
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from rest_framework.authtoken.models import Token


class Account(AbstractBaseUser):
	# id = models.IntegerField(primary_key=True, auto_created=True)
	first_name = models.CharField('first_name', max_length=30, blank=False, null=False)
	last_name = models.CharField('last_name', max_length=30, blank=False, null=False)
	username = models.CharField('username', max_length=20, unique=True, null=False, blank=False)
	password = models.CharField('password', max_length=128)
	email = models.EmailField('email', max_length=60, unique=True, default=None)
	status = models.CharField('status', max_length=10, blank=False, null=False, default='INACTIVE')

	date_joined = DateTimeUTCField('date_joined', auto_now_add=True)
	last_login = DateTimeUTCField('last_login', auto_now_add=True)
	modified = DateTimeUTCField('modified', auto_now_add=True)
	is_admin = models.BooleanField('is_admin', default=False)
	is_staff = models.BooleanField('is_staff', default=False)
	is_superuser = models.BooleanField('is_superuser', default=False)

	USERNAME_FIELD = 'email'

	def __str__(self):
		return self.username

	def has_perm(self, *args, **kwargs):
		return self.is_admin

	def has_module_perms(self, *args, **kwargs):
		return self.is_admin
