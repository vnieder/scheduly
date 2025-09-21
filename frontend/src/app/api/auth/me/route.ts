import { NextRequest, NextResponse } from "next/server";

export const GET = async (req: NextRequest) => {
  try {
    // Get the session cookie
    const sessionCookie = req.cookies.get("auth0_session");

    if (!sessionCookie) {
      return NextResponse.json({ error: "No session found" }, { status: 401 });
    }

    // Parse the session data
    const sessionData = JSON.parse(sessionCookie.value);

    if (!sessionData.user) {
      return NextResponse.json(
        { error: "No user in session" },
        { status: 401 }
      );
    }

    return NextResponse.json(sessionData.user);
  } catch {
    return NextResponse.json({ error: "Invalid session" }, { status: 401 });
  }
};
