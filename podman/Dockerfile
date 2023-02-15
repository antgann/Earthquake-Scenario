FROM python:3.6-bullseye

RUN apt-get -qq update
RUN apt-get install --yes apache2 apache2-dev
RUN pip install mod_wsgi
COPY apache2.conf /etc/apache2
COPY ports.conf /etc/apache2
COPY 000-default.conf /etc/apache2/sites-available

RUN mkdir /app
RUN mkdir /app/eew
RUN mkdir /app/eew/EEWScenario

COPY ./deploycode /app/eew/EEWScenario

WORKDIR /app/eew/EEWScenario

RUN mkdir ./amq
RUN mkdir ./amq/conf

COPY activemq/users.properties ./amq/conf
COPY activemq/userInfo.properties ./amq/conf

COPY requirements.yml .
RUN pip install -r requirements.yml

RUN chown -R www-data:www-data /app/eew/EEWScenario
RUN chmod 755 /app/eew/EEWScenario

CMD mod_wsgi-express start-server /app/eew/EEWScenario/EEWScenario/wsgi.py --url-alias /static static --user www-data --group www-data
