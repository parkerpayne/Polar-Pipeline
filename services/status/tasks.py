from celery import Celery

app = Celery('tasks', broker='pyamqp://guest:guest@rabbitmq:5672/')