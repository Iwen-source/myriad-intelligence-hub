@echo off
set DB_PASSWORD=123456
set MAVEN_HOME=D:\java\apache-maven-3.9.16
set PATH=%MAVEN_HOME%\bin;%PATH%
cd /d "G:\毕业设计\ai-empowerment-platform\backend"
mvn spring-boot:run -DskipTests
