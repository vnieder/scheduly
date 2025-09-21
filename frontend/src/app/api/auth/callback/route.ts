import { NextRequest, NextResponse } from "next/server";

export const GET = async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);

  // Get Auth0 configuration from environment variables
  const auth0Domain =
    process.env.AUTH0_ISSUER_BASE_URL?.replace("https://", "") ||
    process.env.AUTH0_DOMAIN;
  const auth0ClientId = process.env.AUTH0_CLIENT_ID;
  const auth0BaseUrl = process.env.AUTH0_BASE_URL;

  // Fallback to detecting the base URL from the request
  const baseUrl =
    auth0BaseUrl || `${req.nextUrl.protocol}//${req.nextUrl.host}`;

  if (!auth0Domain || !auth0ClientId) {
    return NextResponse.json(
      {
        error: "Auth0 configuration missing",
        details: { auth0Domain, auth0ClientId, baseUrl },
      },
      { status: 500 }
    );
  }

  // Handle the callback from Auth0
  const code = searchParams.get("code");
  const state = searchParams.get("state");

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
        redirect_uri: `${baseUrl}/api/auth/callback`,
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
    const response = NextResponse.redirect(`${baseUrl}/`);

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
};
