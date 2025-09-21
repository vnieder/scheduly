import { NextRequest, NextResponse } from "next/server";

export const GET = async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const action = searchParams.get("action") || "login";

  // Get Auth0 configuration from environment variables
  const auth0Domain =
    process.env.AUTH0_ISSUER_BASE_URL?.replace("https://", "") ||
    process.env.AUTH0_DOMAIN;
  const auth0ClientId = process.env.AUTH0_CLIENT_ID;
  const auth0BaseUrl = process.env.AUTH0_BASE_URL;

  if (!auth0Domain || !auth0ClientId || !auth0BaseUrl) {
    return NextResponse.json(
      { error: "Auth0 configuration missing" },
      { status: 500 }
    );
  }

  if (action === "login") {
    // Redirect to Auth0 login
    const loginUrl = new URL(`https://${auth0Domain}/authorize`);
    loginUrl.searchParams.set("response_type", "code");
    loginUrl.searchParams.set("client_id", auth0ClientId);
    loginUrl.searchParams.set(
      "redirect_uri",
      `${auth0BaseUrl}/api/auth/callback`
    );
    loginUrl.searchParams.set("scope", "openid profile email");
    loginUrl.searchParams.set("state", "login");

    return NextResponse.redirect(loginUrl.toString());
  }

  if (action === "logout") {
    // Redirect to Auth0 logout
    const logoutUrl = new URL(`https://${auth0Domain}/v2/logout`);
    logoutUrl.searchParams.set("client_id", auth0ClientId);
    logoutUrl.searchParams.set("returnTo", auth0BaseUrl);

    return NextResponse.redirect(logoutUrl.toString());
  }

  // Callback is now handled by /api/auth/callback/route.ts
  // This route only handles login and logout

  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
};
