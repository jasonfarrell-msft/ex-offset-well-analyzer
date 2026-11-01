# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS client-build
WORKDIR /src/client
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
ARG VITE_ENABLE_OFFSET_PREVIEW=false
RUN VITE_ENABLE_OFFSET_PREVIEW="$VITE_ENABLE_OFFSET_PREVIEW" npm run build

FROM mcr.microsoft.com/dotnet/sdk:10.0-noble AS server-build
ARG NUGET_SOURCE=https://api.nuget.org/v3/index.json
WORKDIR /src
COPY api/ ./api/
COPY server/ ./server/
RUN dotnet restore server/DrillAdvisor.Web.Tests/DrillAdvisor.Web.Tests.csproj \
    --source "$NUGET_SOURCE"
RUN dotnet test server/DrillAdvisor.Web.Tests/DrillAdvisor.Web.Tests.csproj \
    --configuration Release \
    --no-restore
COPY --from=client-build /src/client/dist/ ./server/DrillAdvisor.Web/wwwroot/
RUN dotnet publish server/DrillAdvisor.Web/DrillAdvisor.Web.csproj \
    --configuration Release \
    --no-restore \
    --output /app/publish \
    /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0-noble-chiseled-extra AS final
WORKDIR /app
ENV ASPNETCORE_HTTP_PORTS=8080 \
    DOTNET_EnableDiagnostics=0
EXPOSE 8080
COPY --from=server-build --chown=$APP_UID:$APP_UID /app/publish/ ./
USER $APP_UID
ENTRYPOINT ["dotnet", "DrillAdvisor.Web.dll"]
