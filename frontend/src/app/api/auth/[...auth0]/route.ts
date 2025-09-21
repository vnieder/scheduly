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

  if (action === "callback") {
    // Handle the callback from Auth0
    const code = searchParams.get("code");

    if (!code) {
      return NextResponse.json(
        { error: "Authorization code missing" },
        { status: 400 }
      );
    }

    // Exchange code for tokens
    try {
      const tokenResponse = await fetch(`https://${auth0Domain}/oauth/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          grant_type: "authorization_code",
          client_id: auth0ClientId,
          client_secret: process.env.AUTH0_CLIENT_SECRET,
          code,
          redirect_uri: `${auth0BaseUrl}/api/auth/callback`,
        }),
      });

      const tokens = await tokenResponse.json();

      if (!tokenResponse.ok) {
        return NextResponse.json(
          { error: "Token exchange failed", details: tokens },
          { status: 400 }
        );
      }

      // Get user info
      const userResponse = await fetch(`https://${auth0Domain}/userinfo`, {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      const user = await userResponse.json();

      // Create response with redirect to home page
      const response = NextResponse.redirect(`${auth0BaseUrl}/`);

      // Set session cookie (you might want to use a more secure session management)
      response.cookies.set("auth0_session", JSON.stringify({ user, tokens }), {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7 days
      });

      return response;
    } catch (error) {
      return NextResponse.json(
        { error: "Authentication failed", details: error },
        { status: 500 }
      );
    }
  }

  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
};
