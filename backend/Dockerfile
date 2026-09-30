# 后端构建
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B -q
COPY src ./src
RUN mvn package -DskipTests -B -q

# 运行镜像
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# 时区
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

# 创建非root用户
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=build /app/target/*.jar app.jar
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8088

# ⚠️ 安全警告：生产环境运行容器时必须通过 -e 参数注入以下环境变量：
#   docker run -e DB_PASSWORD='your_prod_password' -e JWT_SECRET='your_random_secret' ...
# 当前使用占位符，不可用于生产环境！
ENV SPRING_PROFILES_ACTIVE=redis
ENV DB_PASSWORD=CHANGE_ME_IN_PRODUCTION
ENV JWT_SECRET=CHANGE_ME_IN_PRODUCTION_JWT_SECRET

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8088/api/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
