import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n.ts");

const nextConfig = {
  reactStrictMode: true,
  // typedRoutes is disabled because our routes are locale-templated
  // (`/${locale}/board/${sid}`) and the typed-route scaffold generator
  // can't represent those without a stringly-cast — cast noise isn't
  // worth it. Standard link checking + runtime 404 covers us.
  experimental: {
    typedRoutes: false,
  },
};

export default withNextIntl(nextConfig);
