FROM python:slim
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD *.py .
ADD configserver.yaml .
EXPOSE 8000
CMD ["uvicorn","--host=0.0.0.0","configserver:app"]