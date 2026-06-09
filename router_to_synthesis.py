def route_question(question):
    if "map" in question.lower():
        return "map"
    if "shi" in question.lower() or "score" in question.lower():
        return "table"
    return "text"


def router_to_synthesis(question):
    route = route_question(question)

    return {
        "question": question,
        "route": route,
        "message": "This question should now be passed to the synthesis module."
    }


if __name__ == "__main__":
    print(router_to_synthesis("What is the SHI score for The Hague?"))
