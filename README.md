# Django Elasticemail 


This will allow you to use [elasticemail.com](https://elasticemail.com) as your EmailBackend. The best part is elasticemail.com let you 
send 1.5Lakh emails for free :D [https://elasticemail.com/pricing/](https://elasticemail.com/pricing/)


1. Install the package via git `git install -e git+https://github.com/rrmerugu/django_elasticemail`

2. Add `django_elasticemail` to `INSTALLED_APPS`

3. In `settings.py` add `EMAIL_BACKEND = "django_elasticemail.mail.ElasticEmailBackend"`


## Usage


```python
from django.core.mail import EmailMultiAlternatives


email_message = EmailMultiAlternatives(subject=None, body=None,
                            from_email='xxx@gmail.com',  to=['yy@gmail.com', 'zz@outlook.com'])
email_message.template = 'template-name' # template with this name should be created in your elasticemail.com account
email_message.merge_vars = {
    'text': 'Hello World',
}
email_message.send()

```
